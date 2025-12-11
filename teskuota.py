import os
import google.generativeai as genai
from google.api_core import exceptions
from dotenv import load_dotenv


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Environment variable GEMINI_API_KEY tidak ditemukan.")
        print("   Set dulu, contoh:")
        print('   export GEMINI_API_KEY="API_KEY_KAMU"')
        return

    print("🔑 GEMINI_API_KEY ditemukan, mencoba konek ke Gemini...")

    # Konfigurasi client
    genai.configure(api_key=api_key)

    try:
        # Pakai model yang sama dengan di TripCraft (kalau beda, ganti di sini)
        model = genai.GenerativeModel("gemini-2.5-flash")

        print("🤖 Mengirim test prompt singkat ke Gemini...")
        response = model.generate_content("Say hello in one short sentence.")

        # Kalau sukses, harusnya ada response.text
        print("✅ Request BERHASIL!")
        print("   Response singkat dari Gemini:")
        print("   ------------------------------")
        print(response.text.strip())
        print("   ------------------------------")

    except exceptions.ResourceExhausted as e:
        print("❌ QUOTA ERROR (ResourceExhausted / 429)")
        print("   Artinya kuota untuk model ini habis atau limit = 0.")
        print()
        print("   Detail error:")
        print(f"   {e}")
    except exceptions.PermissionDenied as e:
        print("❌ PERMISSION / API KEY ERROR (403)")
        print("   Cek apakah API key punya akses ke Gemini API.")
        print()
        print("   Detail error:")
        print(f"   {e}")
    except exceptions.InvalidArgument as e:
        print("❌ INVALID ARGUMENT (400)")
        print("   Biasanya karena nama model salah atau format request salah.")
        print()
        print("   Detail error:")
        print(f"   {e}")
    except Exception as e:
        print("❌ Error tak terduga saat memanggil Gemini:")
        print(f"   {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
