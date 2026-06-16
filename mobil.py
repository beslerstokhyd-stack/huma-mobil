# -*- coding: utf-8 -*-
import streamlit as st
from pymongo import MongoClient
import certifi
from datetime import datetime
import urllib.parse
import hashlib
import uuid

# --- VERİTABANI BAĞLANTISI ---
USER = "admin"
PASS = urllib.parse.quote_plus("Hs19051905")
CLUSTER = "cluster0.p1ojawz.mongodb.net"
DB_NAME = "SivasLojistikDB"
CONNECTION_STRING = f"mongodb+srv://{USER}:{PASS}@{CLUSTER}/?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"

def sifre_hashle(sifre):
    return hashlib.sha256(str(sifre).encode()).hexdigest() if sifre else ""

@st.cache_resource
def get_db():
    try:
        client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
        return client[DB_NAME]
    except Exception as e:
        st.error(f"Veritabanı Bağlantı Hatası: {e}")
        return None

db = get_db()

# --- ARAYÜZ TASARIMI ---
st.set_page_config(page_title="Sivas Lojistik Mobil", page_icon="🚛", layout="centered")

# --- OTURUM YÖNETİMİ ---
if 'login' not in st.session_state: st.session_state.update({'login': False, 'role': 'user'})

# --- GİRİŞ EKRANI ---
if not st.session_state['login']:
    st.title("🚛 Sivas Lojistik")
    if db is not None:
        # ARACLAR koleksiyonundan plakaları çek
        arac_docs = list(db["Araclar"].find({}, {"plaka": 1}))
        araclar = [a.get("plaka") for a in arac_docs if a.get("plaka")]
        
        secenekler = ["Plaka Seçiniz...", "⭐ YÖNETİCİ GİRİŞİ"] + araclar
        secim = st.selectbox("🚛 Giriş Türü / Araç Seçin", secenekler)
        
        k_adi = st.text_input("👤 Kullanıcı Adı") if secim == "⭐ YÖNETİCİ GİRİŞİ" else ""
        sifre = st.text_input("🔑 Şifreniz", type="password")
        
        if st.button("SİSTEME GİRİŞ YAP"):
            hashli = sifre_hashle(sifre)
            if secim == "⭐ YÖNETİCİ GİRİŞİ":
                # Personel koleksiyonu üzerinden kontrol
                u = db["Personel"].find_one({"username": k_adi.upper(), "password": hashli, "yetki_seviyesi": {"$in": [0, 1]}})
                if u:
                    st.session_state.update({'login': True, 'role': 'admin', 'user': u['username'], 'plaka': 'MERKEZ'})
                    st.rerun()
                else: st.error("❌ Hatalı Giriş!")
            elif secim != "Plaka Seçiniz...":
                arac = db["Araclar"].find_one({"plaka": secim})
                if arac:
                    mobil_user = arac.get("mobil_user")
                    u = db["Personel"].find_one({"username": str(mobil_user).upper()})
                    if u and str(u.get("password")) == hashli:
                        st.session_state.update({'login': True, 'role': 'user', 'plaka': secim, 'user': u['username']})
                        st.rerun()
                    else: st.error("❌ Hatalı Şifre!")

# --- PANEL MANTIĞI ---
elif st.session_state['role'] == 'admin':
    st.title("📊 Filo Komuta Merkezi")
    if st.sidebar.button("🚪 ÇIKIŞ"): st.session_state['login'] = False; st.rerun()
    # Yönetici paneli kodlarınız buraya devam edecek...

else: # Şoför Paneli
    st.sidebar.markdown(f"### 👤 {st.session_state.get('user', '')}\n### 🆔 {st.session_state.get('plaka', '')}")
    tab1, tab2, tab3, tab4 = st.tabs(["📍 SEFER", "⛽ YAKIT", "💰 MASRAF", "📋 GEÇMİŞİM"])
    
    with tab1:
        sefer = db["Seferler"].find_one({"plaka": st.session_state['plaka'], "durum": "BEKLEMEDE"})
        if sefer:
            c_km = st.number_input("Çıkış KM", min_value=0.0)
            d_km = st.number_input("Dönüş KM", min_value=0.0)
            if st.button("SEFERİ TAMAMLA"):
                if 0 < c_km < d_km:
                    db["Seferler"].update_one({"_id": sefer["_id"]}, {"$set": {"depo_cikis_km": float(c_km), "donus_km": float(d_km), "durum": "TAMAMLANDI", "bitis_zamani": datetime.now()}})
                    st.success("Sefer Kapatıldı!"); st.rerun()
                else: st.error("Geçersiz KM!")
        else: st.info("Aktif sefer yok.")

    with tab2:
        lt = st.number_input("Litre", min_value=0.0)
        fiyat = st.number_input("Litre Fiyatı", min_value=0.0)
        if st.button("YAKIT GÖNDER"):
            if lt > 0:
                db["Giderler"].insert_one({"tarih": datetime.now().strftime("%d/%m/%Y"), "plaka": st.session_state['plaka'], "tur": "YAKIT", "tutar": float(lt*fiyat), "sofor": st.session_state['user'], "kaynak": "MOBIL"})
                st.success("Yakıt kaydedildi!")

    with tab3:
        m_tip = st.selectbox("Tür", ["Yemek", "Tamir", "Bakım", "Diğer"])
        m_tutar = st.number_input("Tutar", min_value=0.0)
        if st.button("MASRAFI KAYDET"):
            if m_tutar > 0:
                db["Giderler"].insert_one({"tarih": datetime.now().strftime("%d/%m/%Y"), "plaka": st.session_state['plaka'], "tur": m_tip.upper(), "tutar": float(m_tutar), "sofor": st.session_state['user'], "kaynak": "MOBIL"})
                st.success("Masraf kaydedildi.")

    with tab4:
        st.subheader("Son Kayıtlarım")
        for k in db["Giderler"].find({"sofor": st.session_state['user']}).sort("_id", -1).limit(5):
            st.write(f"📅 {k['tarih']} | {k['tur']} | {k['tutar']:.2f} ₺")

    if st.sidebar.button("🚪 ÇIKIŞ YAP"): st.session_state['login'] = False; st.rerun()
