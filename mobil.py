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
    if not sifre: return ""
    if len(str(sifre)) == 64: return sifre
    return hashlib.sha256(str(sifre).encode()).hexdigest()

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

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; background-color: #2ecc71; color: white; border: none; }
    .status-box { padding: 20px; border-radius: 15px; background-color: #161b22; border-left: 6px solid #3498db; color: white; margin-bottom: 20px; }
    .admin-card { padding: 15px; border-radius: 10px; background-color: #1e2329; border: 1px solid #3498db; margin-bottom: 10px; }
    .calc-box { padding: 20px; border-radius: 15px; background-color: #1e2329; border: 1px solid #2ecc71; text-align: center; margin-top: 15px; }
    .metric-val { color: #2ecc71; font-size: 30px; font-weight: bold; }
    .empty-card { padding: 10px; border-radius: 10px; background-color: #161b22; border: 1px solid #2ecc71; margin-bottom: 5px; color: #2ecc71; }
    </style>
    """, unsafe_allow_html=True)

if 'login' not in st.session_state: st.session_state.update({'login': False, 'role': 'user'})

# --- GİRİŞ EKRANI ---
if not st.session_state['login']:
    st.title("🚛 Sivas Lojistik")
    if db is not None:
        try:
            araclar = [a.get("plaka") for a in db["Araclar"].find({}, {"plaka": 1}) if a.get("plaka")]
            secim = st.selectbox("🚛 Giriş Türü / Araç Seçin", ["Plaka Seçiniz...", "⭐ YÖNETİCİ GİRİŞİ"] + araclar)
            k_adi = st.text_input("👤 Yönetici Kullanıcı Adı") if secim == "⭐ YÖNETİCİ GİRİŞİ" else ""
            sifre = st.text_input("🔑 Şifreniz", type="password")
            
            if st.button("SİSTEME GİRİŞ YAP"):
                hashli = sifre_hashle(sifre)
                if secim == "⭐ YÖNETİCİ GİRİŞİ":
                    u = db["Kullanicilar"].find_one({"username": k_adi.upper(), "password": hashli, "yetki_seviyesi": {"$in": [0, 1]}})
                    if u: st.session_state.update({'login': True, 'role': 'admin', 'user': u['username'], 'plaka': 'MERKEZ'}); st.rerun()
                    else: st.error("❌ Hatalı Giriş!")
                elif secim != "Plaka Seçiniz...":
                    arac = db["Araclar"].find_one({"plaka": secim})
                    u = db["Kullanicilar"].find_one({"username": str(arac.get("mobil_user", "")).upper()}) if arac else None
                    if u and str(u.get("password")) == hashli:
                        st.session_state.update({'login': True, 'role': 'user', 'plaka': secim, 'user': u['username']}); st.rerun()
                    else: st.error("❌ Yetkisiz veya Hatalı Giriş!")
        except Exception as e: st.error(f"Sistem Hatası: {e}")

# --- YÖNETİCİ PANELİ ---
elif st.session_state['role'] == 'admin':
    st.title("📊 Filo Komuta Merkezi")
    # ... (Yönetici panelinizdeki kodlar aynen çalışmaya devam eder) ...
    if st.sidebar.button("🚪 ÇIKIŞ"): st.session_state['login'] = False; st.rerun()

# --- ŞOFÖR PANELİ ---
else:
    st.sidebar.markdown(f"### 👤 {st.session_state['user']}\n### 🆔 {st.session_state['plaka']}")
    tab1, tab2, tab3, tab4 = st.tabs(["📍 SEFER", "⛽ YAKIT", "💰 MASRAF", "📋 GEÇMİŞİM"])

    with tab1:
        sefer = db["Seferler"].find_one({"plaka": st.session_state['plaka'], "durum": "BEKLEMEDE"})
        if sefer:
            c_km = st.number_input("Çıkış KM", min_value=0.0, step=1.0)
            d_km = st.number_input("Dönüş KM", min_value=0.0, step=1.0)
            if st.button("SEFERİ TAMAMLA"):
                if 0 < c_km < d_km:
                    db["Seferler"].update_one({"_id": sefer["_id"]}, {"$set": {"depo_cikis_km": float(c_km), "donus_km": float(d_km), "durum": "TAMAMLANDI", "bitis_zamani": datetime.now()}})
                    st.success("Sefer başarıyla kapatıldı!"); st.rerun()
                else: st.error("KM değerlerini kontrol edin!")
        else: st.info("Aktif sefer yok."); st.button("🔄 Yenile")

    with tab2:
        lt = st.number_input("Litre", min_value=0.0, step=0.01)
        fiyat = st.number_input("Litre Fiyatı", min_value=0.0, step=0.01)
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

    with tab4: # EKSİKLİĞİ GİDEREN YENİ TAB
        st.subheader("Son 5 Kaydım")
        kayitlar = list(db["Giderler"].find({"sofor": st.session_state['user']}).sort("_id", -1).limit(5))
        for k in kayitlar:
            st.markdown(f"**{k['tarih']}** - {k['tur']} : **{k['tutar']:.2f} ₺**")

    if st.sidebar.button("🚪 ÇIKIŞ YAP"): st.session_state['login'] = False; st.rerun()
