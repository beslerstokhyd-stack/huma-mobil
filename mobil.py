import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Hüma Lojistik Mobil", page_icon="🚚", layout="centered")

# 2. VERİTABANI BAĞLANTISI
# Bu fonksiyon veritabanına güvenli ve hızlı bağlanmanı sağlar.
@st.cache_resource
def init_connection():
    # Şifrendeki noktaya ve kullanıcı adına dokunmadan bağlantıyı kuruyoruz.
    return MongoClient("mongodb+srv://beslerstokhyd:Asdfgh123.@cluster0.v8v6f.mongodb.net/?retryWrites=true&w=majority")

client = init_connection()
# Atlas panelinde görünen gerçek veritabanı adın
db = client["SivasLojistikDB"] 

# 3. GİRİŞ KONTROLÜ (Session State)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🚚 Hüma Lojistik Giriş")
    st.subheader("Lütfen Bilgilerinizi Giriniz")
    
    user_input = st.text_input("Kullanıcı Adı")
    sifre_input = st.text_input("Şifre", type="password")
    
    if st.button("SİSTEME GİRİŞ YAP"):
        # Kullanicilar tablosundan kullanıcıyı ve şifreyi sorguluyoruz
        kullanici = db["Kullanicilar"].find_one({"username": user_input, "password": sifre_input})
        
        if kullanici:
            st.session_state['logged_in'] = True
            st.session_state['user_name'] = user_input
            
            # Personel tablosundan şoförün üzerine kayıtlı plakayı çekiyoruz
            p_bilgi = db["Personel"].find_one({"username": user_input})
            st.session_state['plaka'] = p_bilgi.get("atanan_plaka", "ARAÇSIZ") if p_bilgi else "ARAÇSIZ"
            
            st.success("Giriş Başarılı! Yönlendiriliyorsunuz...")
            st.rerun()
        else:
            st.error("Hatalı Kullanıcı Adı veya Şifre! Lütfen panelden bilgilerinizi kontrol edin.")

else:
    # 4. ANA UYGULAMA PANELİ (Giriş Yapıldıktan Sonra Görünecek Kısım)
    with st.sidebar:
        st.header("Hüma Lojistik")
        st.write(f"👤 **Şoför:** {st.session_state['user_name']}")
        st.write(f"🚛 **Plaka:** {st.session_state['plaka']}")
        if st.button("Güvenli Çıkış"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.title(f"Plaka: {st.session_state['plaka']}")
    
    tab1, tab2 = st.tabs(["📍 SEFER TAKİBİ", "💰 MASRAF VE YAKIT"])

    # --- SEFER TABI ---
    with tab1:
        st.subheader("Aktif Sefer Bilgisi")
        # Seferler tablosunda bu plakaya ait beklemede olan seferi ara
        sefer = db["Seferler"].find_one({
            "plaka": {"$regex": st.session_state['plaka'].replace(" ", ""), "$options": "i"},
            "durum": {"$in": ["BEKLEYOR", "BEKLEMEDE", "AKTİF"]}
        })
        
        if sefer:
            st.info(f"✅ Sefer: {sefer.get('guzergah', 'Güzergah Belirtilmedi')}")
            yeni_km = st.number_input("Güncel Kilometre Giriniz", min_value=0)
            if st.button("KİLOMETREYİ KAYDET"):
                db["Seferler"].update_one({"_id": sefer["_id"]}, {"$set": {"fiili_km": yeni_km, "guncelleme": datetime.now()}})
                st.success("Kilometre başarıyla güncellendi.")
        else:
            st.warning("Üzerinize tanımlı aktif bir sefer bulunamadı.")

    # --- MASRAF TABI ---
    with tab2:
        st.subheader("Masraf / Yakıt Girişi")
        m_tip = st.selectbox("Harcama Türü", ["Yakıt", "Yemek", "Tamir", "Otoyol", "Diğer"])
        m_tutar = st.number_input("Tutar (₺)", min_value=0.0)
        m_not = st.text_area("Not (Opsiyonel)")
        
        if st.button("KAYDI MERKEZE GÖNDER"):
            if m_tutar > 0:
                db["Giderler"].insert_one({
                    "tarih": datetime.now(),
                    "plaka": st.session_state['plaka'],
                    "sofor": st.session_state['user_name'],
                    "kategori": m_tip,
                    "tutar": m_tutar,
                    "not": m_not
                })
                st.success("Harcama kaydı başarıyla gönderildi.")
            else:
                st.error("Lütfen bir tutar giriniz!")