#!/usr/bin/env python3
"""
HƏQIQI DÜNYA NÜMUNƏLƏRI
Real-world usage examples
"""

print("=" * 80)
print("PARCER - HƏQIQI DÜNYA NÜMUNƏLƏRI".center(80))
print("=" * 80)

examples = [
    {
        "başlıq": "1. Almashop mağazasının bütün məhsullarını tap",
        "komanda": 'py parcer/parcer.py --store "Almashop" --output almashop.json',
        "izahat": "Almashop-dan bütün məhsullar 10 səhifədən toplanacaq"
    },
    {
        "başlıq": "2. Konkret mağazanın konkret kateqoriyadaki məhsulları",
        "komanda": 'py parcer/parcer.py --store "Almashop" --cat "Elektronika" --output apple_products.json',
        "izahat": "Almashop-dan sadəcə Elektronika kateqoriyadaki məhsullar"
    },
    {
        "başlıq": "3. Avtomobil mağazasından maşınları tap",
        "komanda": 'py parcer/parcer.py --store "Avto Chayna" --cat "Nəqliyyat" --output avto.json',
        "izahat": "Avto Chayna-nın Nəqliyyat bölməsindəki məhsullar"
    },
    {
        "başlıq": "4. Bütün mağazaları qruplaşdır",
        "komanda": "py parcer/parcer.py --group-by-store --output all_stores.json",
        "izahat": "Bütün məhsullar mağaza adına görə qruplaşdırılacaq"
    },
    {
        "başlıq": "5. CSV formatında export et",
        "komanda": 'py parcer/parcer.py --store "Almashop" --cat "Elektronika" --csv --output apple.csv',
        "izahat": "Excel-də açılacaq CSV formatında"
    },
    {
        "başlıq": "6. Məhsulları konsolda göstər",
        "komanda": 'py parcer/parcer.py --store "Kamran" --json',
        "izahat": "Kamran mağazasındakı məhsullar formatlanmış JSON olaraq göstəriləcək"
    }
]

for ex in examples:
    print(f"\n{ex['başlıq']}")
    print("-" * 80)
    print(f"Komanda:\n  {ex['komanda']}")
    print(f"\nİzahat: {ex['izahat']}")

print("\n" + "=" * 80)
print("KƏY MƏLUMATLAR".center(80))
print("=" * 80)

info = """
✅ SADƏ SINTAKSI İSTİFADƏ EDIN:
   --store  : Mağaza adı
   --cat    : Kateqoriya (isteğe bağlı)

❌ XATIRLA - BU LAZIM DEĞİL:
   --url     (avtomatik olaraq tapılacaq)
   --pages   (standart 10 səhifə)

💡 İPUÇLAR:
   • Mağaza adında böyük/kiçik hərf fərqi yoxdur
   • Qismən adlar da işləyir: "Alma" -> "Almashop"
   • Kateqoriyada da böyük/kiçik hərf fərqi yoxdur
   • CSV çıxışı üçün --csv flag-ini əlavə edin

📝 ÇIKIŞ FORMATLARı:
   • JSON : --output file.json (standart)
   • CSV  : --csv --output file.csv
   • Konsol: --json (--output olmadan)
"""

print(info)

print("=" * 80)
print("İndi başla!".center(80))
print("=" * 80)
