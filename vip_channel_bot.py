import requests
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Konfigurasi logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Token Bot Telegram
BOT_TOKEN = "7036261774:AAEQdIKvkfh4hKgSAoWrRKN57cEMDSP7yGo"

# ID Channel VIP & Admin
VIP_CHANNEL_ID = -1002592876178
ADMIN_ID = 7666959350

# Data Pembayaran
PAYPAL_LINK = "https://www.paypal.me/AllennaMaily/1?currencyCode=USD"
GOPAY_QR_LINK = "https://drive.google.com/file/d/1y7-_CBo9qrzdctcFssez1vEfLfenwvPO/view?usp=drivesdk"
HARGA_VIP = 20000  # Harga dalam Rupiah (IDR)

# Simpan transaksi yang sedang diverifikasi
pending_verifications = {}

# Fungsi untuk mengirim notifikasi error ke admin
async def lapor_admin(context: ContextTypes.DEFAULT_TYPE, pesan: str):
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🚨 *ERROR di Bot VIP:*\n{pesan}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Gagal mengirim laporan ke admin: {e}")

# Perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = (
            "🎉 *Selamat datang di Bot VIP!*\n\n"
            f"💎 Untuk mendapatkan akses ke *Channel VIP*, lakukan pembayaran sebesar {HARGA_VIP} IDR atau 1,4 USD.\n\n"
            "📌 *Pilih metode pembayaran:*\n"
            f"1. PayPal: [Klik di sini]({PAYPAL_LINK})\n"
            f"2. GoPay: Kirim ke QR berikut:\n"
            f"[Klik untuk scan QR pembayaran]({GOPAY_QR_LINK})\n\n"
            "Setelah membayar, ketik `/verify [id_transaksi]` untuk verifikasi."
        )
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Kesalahan di perintah /start: {e}")
        await lapor_admin(context, f"Kesalahan di perintah /start: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi nanti.")

# Perintah /verify untuk pengguna
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not context.args:
            await update.message.reply_text("❌ Silakan kirim ID transaksi. Contoh: `/verify ABC12345`")
            return

        user_id = update.message.from_user.id
        username = update.message.from_user.username or "Pengguna"
        id_transaksi = context.args[0]

        if not re.match(r'^[a-zA-Z0-9]{8,}$', id_transaksi):
            await update.message.reply_text("❌ ID transaksi tidak valid. Pastikan Anda memasukkan ID yang benar.")
            return

        pending_verifications[id_transaksi] = user_id

        keyboard = [
            [
                InlineKeyboardButton(text="Salin ID Pengguna", callback_data=f"salin_id_user:{user_id}"),
                InlineKeyboardButton(text="Salin ID Transaksi", callback_data=f"salin_id_transaksi:{id_transaksi}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📩 *Permintaan Verifikasi Pembayaran*\n\n"
                 f"🧑‍💼 Pengguna @{username} (ID: {user_id}) meminta verifikasi pembayaran.\n\n"
                 f"🔢 ID Transaksi: {id_transaksi}\n"
                 "Silakan periksa transaksi dan konfirmasi statusnya.\n\n"
                 "Balas dengan: \n"
                 "1. `/verify_admin ok [user_id]` jika pembayaran valid.\n"
                 "2. `/verify_admin failed [user_id]` jika pembayaran tidak valid.",
            reply_markup=reply_markup
        )

        await update.message.reply_text("✅ Pembayaran Anda telah dikirim untuk verifikasi admin.")
    except Exception as e:
        logging.error(f"Kesalahan saat verifikasi: {e}")
        await lapor_admin(context, f"Kesalahan saat verifikasi: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan internal. Silakan coba lagi nanti.")

# Perintah /verify_admin untuk admin
async def verify_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("❌ Gunakan format: `/verify_admin ok/failed [user_id]`")
            return

        if update.message.from_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Anda bukan admin!")
            return

        action = context.args[0]
        user_id = int(context.args[1])

        if action == "ok":
            if user_id in pending_verifications.values():
                await update.message.reply_text(f"✅ Pembayaran oleh pengguna {user_id} telah diverifikasi.")
                try:
                    invite_link = await context.bot.export_chat_invite_link(VIP_CHANNEL_ID)
                    await context.bot.send_message(chat_id=user_id, text=f"🎉 Selamat! Anda sekarang memiliki akses ke Channel VIP! {invite_link}")
                except Exception as e:
                    logging.error(f"Gagal mengundang pengguna: {e}")
                    await update.message.reply_text(f"❌ Gagal mengundang pengguna {user_id}.")
        elif action == "failed":
            await update.message.reply_text(f"❌ Pembayaran oleh pengguna {user_id} ditolak.")
            await context.bot.send_message(chat_id=user_id, text="❌ Pembayaran Anda tidak valid. Silakan coba lagi.")
        else:
            await update.message.reply_text("❌ Perintah tidak dikenali.")
    except Exception as e:
        logging.error(f"Kesalahan saat verifikasi admin: {e}")
        await lapor_admin(context, f"Kesalahan saat verifikasi admin: {e}")

# Fungsi tombol callback
async def tombol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("salin_id_user:"):
        user_id = query.data.split(":")[1]
        await query.message.reply_text(f"ID Pengguna: {user_id}")
    elif query.data.startswith("salin_id_transaksi:"):
        id_transaksi = query.data.split(":")[1]
        await query.message.reply_text(f"ID Transaksi: {id_transaksi}")

# Menjalankan bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verify", verify))
    application.add_handler(CommandHandler("verify_admin", verify_admin))
    application.add_handler(CallbackQueryHandler(tombol_callback))

    # Jalankan Flask di thread terpisah
    Thread(target=run_flask).start()

    print("🤖 Bot VIP berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
