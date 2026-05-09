import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Hüma Lojistik Mobil", page_icon="🚚", layout="centered")

# 2. VERİTABANI BAĞLANTISI (Atlas Panelindeki Bilgilere Göre)
@st.cache_resource
def init_connection():
    # Şifrendeki noktaya ve kullanıcı adına dikkat ederek bağlantıyı kuruyoruz
    return MongoClient("mongodb+srv://beslerstokhyd:Asdfgh123.@cluster0.v8v6f.mongodb.net/?retryWrites=true&w=majority")

client = init_connection()
# Atlas panelinde görünen gerçek veritabanı adın
db = client["SivasLojistikDB"] 

# 3. GİRİŞ KONTROLÜ
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🚚 Hüma Lojistik Giriş")
    
    user_input = st.text_input("Kullanıcı Adı")
    sifre_input = st.text_input("Şifre", type="password")
    
    if st.button("SİSTEME GİRİŞ YAP"):
        # Kullanicilar tablosundan kontrol
        kullanici = db["Kullanicilar"].find_one({"username": user_input, "password": sifre_input})
        
        if kullanici:
            st.session_state['logged_in'] = True
            st.session_state['user_name'] = user_input
            # Personel tablosundan araç bilgisini çek
            p_bilgi = db["Personel"].find_one({"username": user_input})
            st.session_state['plaka'] = p_bilgi.get("atanan_plaka", "ARAÇSIZ") if p_bilgi else "ARAÇSIZ"
            st.success("Giriş Başarılı!")
            st.rerun()
        else:
            st.error("Hatalı Kullanıcı Adı veya Şifre!")

else:
    # 4. ANA PANEL
    st.sidebar.success(f"Hoş geldin: {st.session_state['user_name']}")
    st.title(f"🚛 Araç: {st.session_state['plaka']}")
    
    tab1, tab2 = st.tabs(["📍 SEFER", "⛽ YAKIT/MASRAF"])

    with tab1:
        # Aktif seferi bul (BEKLEMEDE veya AKTİF olanlar)
        sefer = db["Seferler"].find_one({
            "plaka": {"$regex": st.session_state['plaka'].replace(" ", ""), "$options": "i"},
            "durum": {"$in": ["BEKLEYOR", "BEKLEMEDE", "AKTİF"]}
        })
        
        if sefer:
            st.info(f"Sefer: {sefer.get('guzergah', 'Belirsiz')}")
            yeni_km = st.number_input("Güncel KM", min_value=0)
            if st.button("KM GÜNCELLE"):
                db["Seferler"].update_one({"_id": sefer["_id"]}, {"$set": {"fiili_km": yeni_km}})
                st.success("KM Kaydedildi.")
        else:
            st.warning("Aktif seferiniz bulunmamaktadır.")

    with tab2:
        st.subheader("Masraf Kaydı")
        tip = st.selectbox("Tür", ["Yakıt", "Yemek", "Tamir", "Diğer"])
        tutar = st.number_input("Tutar (₺)", min_value=0.0)
        if st.button("KAYDET"):
            db["Giderler"].insert_one({
                "tarih": datetime.now(),
                "plaka": st.session_state['plaka'],
                "sofor": st.session_state['user_name'],
                "kategori": tip,
                "tutar": tutar
            })
            st.success("Masraf merkeze iletildi.")