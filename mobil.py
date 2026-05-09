# -*- coding: utf-8 -*-
import streamlit as st
from pymongo import MongoClient
import certifi
from datetime import datetime
import urllib.parse

# --- 1. BULUT BAĞLANTI AYARLARI ---
USER = "admin"
PASS = urllib.parse.quote_plus("Hs19051905")
CLUSTER = "cluster0.p1ojawz.mongodb.net"
DB_NAME = "SivasLojistikDB"
CONNECTION_STRING = f"mongodb+srv://{USER}:{PASS}@{CLUSTER}/?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"

@st.cache_resource
def get_db():
    try:
        client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
        return client[DB_NAME]
    except Exception as e:
        st.error(f"Veritabanı Bağlantı Hatası: {e}")
        return None

db = get_db()

# --- 2. SAYFA AYARLARI ---
st.set_page_config(page_title="Hüma Lojistik Mobil", page_icon="🚛", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #2ecc71; color: white; font-weight: bold; }
    .stTextInput>div>div>input { border-radius: 10px; }
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KULLANICI GİRİŞ SİSTEMİ ---
if 'login' not in st.session_state:
    st.session_state['login'] = False

if not st.session_state['login']:
    st.title("🔐 Şoför Giriş Paneli")
    try:
        araclar_data = list(db["Araclar"].find({}, {"plaka": 1}).sort("plaka", 1))
        plakalar = [a["plaka"] for a in araclar_data]
    except:
        plakalar = ["Hata: Araçlar Yüklenemedi"]

    secili_plaka = st.selectbox("Aracınızı Seçin", ["Seçiniz..."] + plakalar)
    sifre = st.text_input("Giriş Şifresi (Plakanın Son 4 Hanesi)", type="password")
    
    if st.button("SİSTEME GİRİŞ YAP"):
        if secili_plaka != "Seçiniz...":
            temiz_plaka = secili_plaka.replace(" ", "").replace("-", "")
            dogru_sifre = temiz_plaka[-4:]
            
            if str(sifre).strip() == str(dogru_sifre):
                st.session_state['login'] = True
                st.session_state['plaka'] = secili_plaka
                arac_bilgi = db["Araclar"].find_one({"plaka": secili_plaka})
                st.session_state['user_name'] = arac_bilgi.get("mobil_user", secili_plaka)
                st.rerun()
            else:
                st.error("❌ Hatalı Şifre!")
        else:
            st.error("⚠️ Lütfen bir plaka seçin.")
else:
    # --- 4. ANA PANEL ---
    st.title(f"🚛 {st.session_state['plaka']}")
    st.caption(f"👤 Şoför: {st.session_state['user_name']}")
    
    if st.sidebar.button("🚪 Güvenli Çıkış"):
        st.session_state['login'] = False
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📍 SEFER TAKİBİ", "⛽ YAKIT ALIMI", "💰 MASRAF YAZ"])
    plaka = st.session_state['plaka']

    # --- TAB 1: SEFER TAKİBİ (PLAKA HATASI DÜZELTİLDİ) ---
    with tab1:
        st.subheader("Sefer Kilometre Takibi")
        
        # Boşlukları silerek esnek arama yapar (Hata önleyici)
        temiz_arama_plakasi = plaka.replace(" ", "")
        aktif_sefer = db["Seferler"].find_one({
            "plaka": {"$regex": temiz_arama_plakasi, "$options": "i"}, 
            "durum": {"$in": ["BEKLEYOR", "AKTİF", "YOLDA"]}
        })
        
        if aktif_sefer:
            st.info(f"**📍 Güncel Rota:** {aktif_sefer.get('rota_ozet', 'Rota Belirtilmemiş')}")
            c_km = st.number_input("Çıkış KM", value=float(aktif_sefer.get("depo_cikis_km", 0)), disabled=True)
            d_km = st.number_input("Dönüş (Varış) KM", min_value=float(c_km), step=1.0)
            
            if st.button("✅ SEFERİ TAMAMLA"):
                if d_km > c_km:
                    fiili = d_km - c_km
                    db["Seferler"].update_one(
                        {"_id": aktif_sefer["_id"]},
                        {"$set": {
                            "donus_km": d_km, 
                            "fiili_km": fiili, 
                            "durum": "TAMAMLANDI",
                            "bitis_tarihi": datetime.now()
                        }}
                    )
                    st.success(f"🎉 Sefer Tamamlandı! Yapılan Yol: {fiili} KM")
                    st.rerun()
                else:
                    st.error("❌ Dönüş KM, çıkıştan büyük olmalıdır!")
        else:
            st.warning("⚠️ Şu an üzerinize tanımlı aktif bir sefer bulunamadı. (Masaüstünden 'BEKLEYOR' durumunda sefer açtığınızdan emin olun)")

    # --- TAB 2: YAKIT ALIMI ---
    with tab2:
        st.subheader("Yakıt Alım Bilgisi")
        litre = st.number_input("Kaç Litre (LT)?", min_value=0.0, step=0.1)
        birim_fiyat = st.number_input("Litre Fiyatı (₺)", min_value=0.0, step=0.01)
        toplam_tutar = round(litre * birim_fiyat, 2)
        st.metric(label="Hesaplanan Toplam Tutar", value=f"{toplam_tutar} ₺")
        istasyon = st.text_input("İstasyon / Şehir")
        
        if st.button("⛽ YAKIT KAYDINI GÖNDER"):
            if toplam_tutar > 0:
                db["Giderler"].insert_one({
                    "tarih": datetime.now(),
                    "plaka": plaka,
                    "sofor": st.session_state['user_name'],
                    "tip": "YAKIT",
                    "miktar": litre,
                    "birim_fiyat": birim_fiyat,
                    "tutar": toplam_tutar,
                    "detay": istasyon,
                    "kaynak": "MOBIL"
                })
                st.success(f"✅ Yakıt kaydı başarıyla iletildi.")
            else:
                st.error("Lütfen miktar giriniz.")

    # --- TAB 3: MASRAFLAR ---
    with tab3:
        st.subheader("Harcama ve Masraf")
        m_tip = st.selectbox("Masraf Türü", ["Yemek", "Tamir", "Otoyol / Köprü", "AdBlue", "Lastik", "Avans", "Park / Yıkama", "DİĞER"])
        m_tutar = st.number_input("Harcama Tutarı (₺)", min_value=0.0, step=1.0)
        aciklama = st.text_area("Masraf Açıklaması")
        
        if st.button("💰 MASRAFI KAYDET"):
            if m_tutar > 0:
                db["Giderler"].insert_one({
                    "tarih": datetime.now(),
                    "plaka": plaka,
                    "sofor": st.session_state['user_name'],
                    "tip": "MASRAF",
                    "kategori": m_tip,
                    "masraf_tipi": m_tip,
                    "tutar": m_tutar,
                    "aciklama": aciklama,
                    "detay": aciklama,
                    "kaynak": "MOBIL"
                })
                st.success("✅ Masraf başarıyla merkeze iletildi.")
            else:
                st.error("Lütfen tutar giriniz.")