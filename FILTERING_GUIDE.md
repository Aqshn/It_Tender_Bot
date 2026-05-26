# PARCER - FILTRLƏMƏ İSTİFADƏ MƏSƏLƏLƏRİ

## 1. Mağaza adı ilə filtrləmə

Bütün məhsullardan sadəcə seçilmiş mağazanın məhsullarını göstər:

```bash
# Almashop mağazasının bütün məhsulları
py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 --filter-store "Almashop" --output almashop_products.json

# Azad mağazasının bütün məhsulları
py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 --filter-store "Azad" --output azad_products.json
```

## 2. Mağaza + Kateqoriya ilə filtrləmə

Seçilmiş mağazanın seçilmiş kateqoriyadaki məhsullarını göstər:

```bash
# Almashop mağazasının Elektronika kateqoriyadaki məhsulları
py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 --filter-store "Almashop" --filter-category "Elektronika" --output almashop_electronics.json

# Almashop mağazasının Ev və bağ üçün kateqoriyadaki məhsulları
py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 --filter-store "Almashop" --filter-category "Ev" --output almashop_home.json
```

## 3. Mağazalara görə qruplaşdırma

Bütün məhsulları mağazalar üzrə qruplaşdır:

```bash
py parcer/parcer.py --url "https://tap.az/elanlar" --pages 5 --group-by-store --output grouped.json
```

## Mağazaların Siyahısı (Mövcud)

- Azad (1 məhsul)
- Sabir (1 məhsul)  
- RAFAEL (1 məhsul)
- Spektrx (1 məhsul)
- Ars Group (1 məhsul)
- Mehri Mmc (1 məhsul)
- Almashop (4 məhsul)
- Techbox (1 məhsul)
- Semistan (1 məhsul)
- Elvin (1 məhsul)
- Həsən (1 məhsul)
- Avto Chayna (2 məhsul)
- İnnovation (1 məhsul)
- Aga (1 məhsul)
- Kamran (2 məhsul)
- Khanelectronics AZ (1 məhsul)
- Fizuli (1 məhsul)
- Rövşən (1 məhsul)
- Elmira (1 məhsul)
- Nazim (1 məhsul)
- Zeyd (1 məhsul)
- Remar (1 məhsul)
- Zauri Abbasov (1 məhsul)

## QEYD

- Filtrləmə **qeyri-həssas** (böyük-kiçik hərflərə diqqət edilmir)
- Filtrləmə **qismən uyğunluq** ilə işləyir (məsələn: "Alma" yazarsa "Almashop" tapıcaq)
- --filter-category sadəcə --filter-store ilə birlikdə istifadə olunur
