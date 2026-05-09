import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Hüma Lojistik Mobil", page_icon="🚚", layout="centered")

# 2. VERİTABANI BAĞLANTISI (Atlas Verileri Buradan Alınıyor)
# Not: Bağlantı adresindeki karakter hataları giderildi.
@st.cache_resource
def init_connection():
    return MongoClient("mongodb+srv://beslerstokhyd:Asdfgh123.@cluster0.v8v6f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

client = init_connection()
db = client["HumaLojistik"]

# 3. GİRİŞ KONTROLÜ
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🚚 Hüma Lojistik Giriş")
    st.subheader("Şoför Giriş Paneli")
    
    user_input = st.text_input("Kullanıcı Adı (Personel Panelindeki Adınız)")
    sifre_input = st.text_input("Şifre (Kendi Belirlediğiniz Özel Şifre)", type="password")
    
    if st.button("SİSTEME GİRİŞ YAP"):
        # Veritabanındaki 'Kullanicilar' tablosundan sorgulama yapıyoruz
        kullanici_kaydi = db["Kullanicilar"].find_one({
            "username": user_input,
            "password": sifre_input
        })
        
        if kullanici_kaydi:
            # Personelin üzerine kayıtlı plakayı çekiyoruz
            personel_detay = db["Personel"].find_one({"username": user_input})
            
            st.session_state['logged_in'] = True
            st.session_state['user_name'] = user_input
            st.session_state['plaka'] = personel_detay.get("atanan_plaka", "BOŞTA") if personel_detay else "BOŞTA"
            st.success("Giriş Başarılı! Yönlendiriliyorsunuz...")
            st.rerun()
        else:
            st.error("Hatalı Kullanıcı Adı veya Şifre! Lütfen Personel Yönetimi'ndeki bilgilerinizi kontrol edin.")

else:
    # 4. ANA UYGULAMA EKRANI
    plaka = st.session_state['plaka']
    
    with st.sidebar:
        st.header("Hüma Lojistik")
        st.write(f"👤 **Şoför:** {st.session_state['user_name']}")
        st.write(f"🚛 **Araç:** {plaka}")
        if st.button("Güvenli Çıkış"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.title(f"Plaka: {plaka}")
    
    tab1, tab2, tab3 = st.tabs(["📍 SEFER TAKİBİ", "⛽ YAKIT ALIMI", "💰 MASRAF YAZ"])

    # --- TAB 1: SEFER TAKİBİ ---
    with tab1:
        st.subheader("Aktif Sefer Bilgileri")
        
        # 'BEKLEMEDE' ve 'BEKLEYOR' durumundaki seferleri Atlas'tan çekiyoruz
        aktif_sefer = db["Seferler"].find_one({
            "plaka": {"$regex": plaka.replace(" ", ""), "$options": "i"},
            "durum": {"$in": ["BEKLEYOR", "BEKLEMEDE", "AKTİF", "YOLDA"]}
        })

        if aktif_sefer and plaka != "BOŞTA":
            st.info(f"✅ Sefer No: {aktif_sefer.get('sefer_no', 'N/A')}")
            st.write(f"📅 **Tarih:** {aktif_sefer.get('tarih', '')}")
            st.write(f"🌍 **Güzergah:** {aktif_sefer.get('guzergah', 'Belirtilmedi')}")
            
            yeni_km = st.number_input("Güncel Kilometre Giriniz", min_value=0)
            if st.button("KİLOMETREYİ GÜNCELLE"):
                db["Seferler"].update_one(
                    {"_id": aktif_sefer["_id"]},
                    {"$set": {"fiili_km": yeni_km, "guncelleme_tarihi": datetime.now()}}
                )
                st.success("Kilometre bilgisi başarıyla güncellendi.")
        else:
            st.warning("⚠️ Şu an üzerinize tanımlı aktif bir sefer bulunamadı. Lütfen masaüstü panelinden sefer durumunu kontrol edin.")

    # --- TAB 2: YAKIT GİRİŞİ ---
    with tab2:
        st.subheader("⛽ Yakıt Bilgisi")
        litre = st.number_input("Alınan Litre", min_value=0.0)
        tutar = st.number_input("Toplam Tutar (₺)", min_value=0.0)
        
        if st.button("YAKIT KAYDINI GÖNDER"):
            db["Yakitlar"].insert_one({
                "tarih": datetime.now(),
                "plaka": plaka,
                "sofor": st.session_state['user_name'],
                "litre": litre,
                "tutar": tutar
            })
            st.success("Yakıt verisi başarıyla Atlas'a gönderildi.")

    # --- TAB 3: MASRAF YAZMA ---
    with tab3:
        st.subheader("💰 Masraf ve Giderler")
        m_tip = st.selectbox("Masraf Türü", ["Yemek", "Tamir", "Otoyol / Köprü", "AdBlue", "Lastik", "Avans", "Park / Yıkama", "DİĞER"])
        m_tutar = st.number_input("Tutar (₺)", min_value=0.0)
        m_not = st.text_area("Masraf Açıklaması")
        
        if st.button("MASRAFI KAYDET"):
            if m_tutar > 0:
                db["Giderler"].insert_one({
                    "tarih": datetime.now(),
                    "plaka": plaka,
                    "sofor": st.session_state['user_name'],
                    "kategori": m_tip,
                    "tutar": m_tutar,
                    "not": m_not,
                    "kaynak": "MOBIL"
                })
                st.success("Masraf kaydı merkeze iletildi.")
            else:
                st.error("Lütfen bir tutar giriniz!")