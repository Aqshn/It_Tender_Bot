# PARCER - SADƏ AXTARIŞ SİNTAKSİ
## Simple Search Syntax Guide

---

## ⚡ SADƏ İSTİFADƏ (Recommended)

### 1. Mağaza adı ilə axtariş
Verilən mağazanın bütün məhsullarını tap:

```bash
py parcer/parcer.py --store "Almashop" --output almashop_products.json
```

**Nəticə**: Almashop mağazasının bütün məhsulları (10 səhifə axtarılır)

---

### 2. Mağaza + Kateqoriya ilə axtarış
Verilən mağazanın seçilmiş kateqoriyadaki məhsullarını tap:

```bash
py parcer/parcer.py --store "Almashop" --cat "Elektronika" --output result.json
```

**Nəticə**: Sadəcə Almashop mağazasının Elektronika kateqoriyadaki məhsulları

---

### 3. Qruplaşdırma
Bütün məhsulları mağazalara görə qruplaşdır:

```bash
py parcer/parcer.py --group-by-store --output all_stores.json
```

**Nəticə**: 
```json
{
  "magazalar": [
    {
      "magaza_adi": "Almashop",
      "mehsullar": [
        { product1 },
        { product2 }
      ]
    }
  ]
}
```

---

## 📋 MƏHSULLARıN SIYAHISI

| Mağaza Adı | Məhsul Sayı |
|-----------|----------|
| Almashop | 4 |
| Avto Chayna | 2 |
| Kamran | 2 |
| Azad | 1 |
| Sabir | 1 |
| RAFAEL | 1 |
| Spektrx | 1 |
| ... və digərləri | ... |

---

## 🔍 FİLTRLƏMƏ QÖYÜDƏLƏRİ

### Hərflər hakkında
- ✅ Böyük/kiçik hərflərə diqqət sız
- ✅ Qismən uyğunluq (məsələn: "Alma" → "Almashop")

### Kateqoriyalar
Aşağıdakı kateqoriyalar istifadə edilə bilər:
- Elektronika
- Ev və bağ üçün
- Nəqliyyat
- Ehtiyat hissələri
- Daşınmaz əmlak
- Xidmətlər
- Şəxsi əşyalar
- Hobbi və asudə
- Məişət texnikası
- Uşaq aləmi
- Heyvanlar
- İş elanları

---

## 💾 ÇIKIŞ FORMATLARı

### JSON (default)
```bash
py parcer/parcer.py --store "Almashop" --output result.json
```

### CSV
```bash
py parcer/parcer.py --store "Almashop" --csv --output result.csv
```

### Konsola yazdır
```bash
py parcer/parcer.py --store "Almashop" --json
```

---

## 📝 NÜMUNƏLƏR

### Nümunə 1: Almashop - Elektronika
```bash
py parcer/parcer.py --store "Almashop" --cat "Elektronika" --output almashop_electronics.json
```

### Nümunə 2: Avto Chayna - Nəqliyyat  
```bash
py parcer/parcer.py --store "Avto Chayna" --cat "Nəqliyyat" --output avto_chayna.json
```

### Nümunə 3: Bütün mağazaların məhsulları
```bash
py parcer/parcer.py --group-by-store --output all_grouped.json
```

---

## ⚙️ ƏSAS SİNTAKSİ (Original)

Daha çox kontrol üçün əsas sintaksidən istifadə edin:

```bash
# URL ilə axtariş
py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 --output result.json

# Filtrləmə ilə
py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 \
  --filter-store "Almashop" --filter-category "Elektronika" --output result.json
```

---

**💡 İpucu**: Sadə axtarış üçün `--store` və `--cat` istifadə edin!
