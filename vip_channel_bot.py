import requests
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Konfigurasi logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Token Bot Telegram (Dapatkan dari @BotFather)
BOT_TOKEN = "7036261774:AAEQdIKvkfh4hKgSAoWrRKN57cEMDSP7yGo"

# ID Channel VIP (format: -100xxxxxxxxxx)
VIP_CHANNEL_ID = -1002592876178

# ID Admin (Dapatkan dari https://t.me/userinfobot)
ADMIN_ID = 7666959350

# Data Pembayaran
PAYPAL_LINK = "https://www.paypal.me/AllennaMaily/1?currencyCode=USD"
GOPAY_QR_LINK = "https://drive.google.com/file/d/1y7-_CBo9qrzdctcFssez1vEfLfenwvPO/view?usp=drivesdk"
HARGA_VIP = 20000  # Harga dalam Rupiah (IDR)

import base64

# Kredensial GoPay (ambil dari dashboard Midtrans Anda) 
GOPAY_SERVER_KEY = "ISI_DENGAN_SERVER_KEY_ANDA"

# Simulasi penyimpanan ID transaksi dan ID pengguna
pending_verifications = {}

# Fungsi untuk mengirim notifikasi ke admin jika terjadi error
async def lapor_admin(context: ContextTypes.DEFAULT_TYPE, pesan: str):
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🚨 *ERROR di Bot VIP:*\n{pesan}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Gagal mengirim laporan ke admin: {e}")

# Fungsi untuk memulai bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = (
            "🎉 *Selamat datang di Bot VIP!*\n\n"
            f"💎 Untuk mendapatkan akses ke *Channel VIP*, lakukan pembayaran sebesar {HARGA_VIP} IDR atau 1,4 USD.\n\n"
            "📌 *Pilih metode pembayaran:*\n"
            f"1. PayPal: [Klik di sini]({PAYPAL_LINK})\n"
            f"2. GoPay: Kirim ke QR berikut:\n"
            f"[Klik untuk scan qr pembayaran]({GOPAY_QR_LINK})\n\n"
            "Setelah membayar, ketik `/verify [id_transaksi]` untuk memverifikasi pembayaran Anda."
        )
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Kesalahan di perintah /start: {e}")
        await lapor_admin(context, f"Kesalahan di perintah /start: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi nanti.")

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
# Fungsi untuk memverifikasi pembayaran secara manual
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not context.args:
            await update.message.reply_text("❌ Silakan kirim ID transaksi. Contoh: `/verify ABC12345`")
            return

        user_id = update.message.from_user.id
        username = update.message.from_user.username or "Pengguna"
        id_transaksi = context.args[0]

        # Validasi ID Transaksi (Minimal 8 karakter, hanya huruf dan angka)
        if not re.match(r'^[a-zA-Z0-9]{8,}$', id_transaksi):
            await update.message.reply_text("❌ ID transaksi tidak valid. Pastikan Anda memasukkan ID yang benar.")
            return

        # Simpan transaksi pengguna untuk verifikasi admin
        pending_verifications[id_transaksi] = user_id

        # Membuat tombol inline untuk salin ID pengguna dan ID transaksi
        keyboard = [
            [
                InlineKeyboardButton(text="Salin ID Pengguna", callback_data=f"salin_id_user:{user_id}"),
                InlineKeyboardButton(text="Salin ID Transaksi", callback_data=f"salin_id_transaksi:{id_transaksi}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Kirim notifikasi ke admin dengan tombol inline
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

        await update.message.reply_text("✅ Pembayaran Anda telah berhasil diverifikasi. Menunggu konfirmasi dari admin.")

    except Exception as e:
        logging.error(f"Kesalahan saat verifikasi: {e}")
        await lapor_admin(context, f"Kesalahan saat verifikasi: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan internal. Silakan coba lagi nanti.")


# Fungsi untuk mengonfirmasi pembayaran dari admin
async def verify_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not context.args:
            await update.message.reply_text("❌ Silakan kirim ID pengguna dan status verifikasi. Contoh: `/verify_ok 123456789`")
            return

        if update.message.from_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Anda bukan admin. Hanya admin yang dapat melakukan verifikasi.")
            return

        action = context.args[0]
        user_id = int(context.args[1])

        if action == "ok":
            # Verifikasi ID pengguna dari transaksi yang telah disimpan
            if user_id in pending_verifications.values():
                await update.message.reply_text(f"✅ Pembayaran oleh pengguna {user_id} telah diverifikasi sebagai valid.")
                # Mengirimkan link undangan ke pengguna
                try:
                    invite_link = await context.bot.export_chat_invite_link(VIP_CHANNEL_ID)
                    await context.bot.send_message(chat_id=user_id, text=f"🎉 Selamat! Pembayaran Anda telah diverifikasi. Anda sekarang memiliki akses ke Channel VIP! {invite_link}")
                    logging.info(f"User {user_id} telah diundang ke Channel VIP.")
                except Exception as e:
                    logging.error(f"Gagal mengundang pengguna ke Channel VIP: {e}")
                    await update.message.reply_text(f"❌ Gagal mengundang pengguna {user_id} ke Channel VIP.")
            else:
                await update.message.reply_text(f"❌ Tidak ditemukan pengguna dengan ID {user_id}.")
        elif action == "failed":
            if user_id in pending_verifications.values():
                await update.message.reply_text(f"❌ Pembayaran oleh pengguna {user_id} ditandai sebagai tidak valid.")
                await context.bot.send_message(chat_id=user_id, text=f"❌ Pembayaran Anda tidak valid. Silakan coba lagi.")
            else:
                await update.message.reply_text(f"❌ Tidak ditemukan pengguna dengan ID {user_id}.")
        else:
            await update.message.reply_text("❌ Perintah tidak dikenali. Gunakan `/verify_ok` atau `/verify_failed`.")

    except Exception as e:
        logging.error(f"Kesalahan saat verifikasi admin: {e}")
        await lapor_admin(context, f"Kesalahan saat verifikasi admin: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi nanti.")

# Fungsi untuk memberikan panduan format verifikasi ID transaksi
async def format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = (
            "📋 *Panduan Format Verifikasi ID Transaksi*:\n\n"
            "Untuk melakukan verifikasi pembayaran, ikuti langkah-langkah berikut:\n\n"
            "1. Lakukan pembayaran sesuai dengan instruksi yang telah diberikan (PayPal atau GoPay).\n"
            "2. Setelah pembayaran, Anda akan menerima ID transaksi dari sistem pembayaran.\n"
            "3. Untuk memverifikasi pembayaran, kirim perintah dengan format berikut:\n\n"
            "/verify [id_transaksi]\n\n"
            "Contoh: `/verify ABC12345`\n\n"
            "Pastikan ID transaksi yang Anda kirimkan valid (minimal 8 karakter, hanya huruf dan angka)."
        )
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Kesalahan saat memberikan panduan format: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi nanti.")

from telegram.ext import CallbackQueryHandler
async def tombol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Menghindari delay

    # Memeriksa apakah tombol yang ditekan untuk salin ID pengguna atau transaksi
    if query.data.startswith("salin_id_user:"):
        user_id = query.data.split(":")[1]
        await query.message.reply_text(f": {user_id}")
    elif query.data.startswith("salin_id_transaksi:"):
        id_transaksi = query.data.split(":")[1]
        await query.message.reply_text(f": {id_transaksi}")


# Menambahkan handler untuk perintah /format
def main():
    # Membuat aplikasi dan menghubungkan token
    application = Application.builder().token(BOT_TOKEN).build()

    # Menambahkan handler untuk perintah /start dan /verify
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verify", verify))
    application.add_handler(CommandHandler("verify_admin", verify_admin))
    application.add_handler(CommandHandler("format", format))

# Menambahkan handler untuk menangani callback tombol
    application.add_handler(CallbackQueryHandler(tombol_callback))

    # Menjalankan polling (menerima pesan dari Telegram)
    print("🤖 Bot VIP berjalan... Menunggu pembayaran...")
    logging.info("🤖 Bot VIP berjalan dan siap menerima pembayaran...")
    application.run_polling()

if __name__ == "__main__":
    main()
