# -*- coding: utf-8 -*-
import streamlit as st
from pymongo import MongoClient
import certifi
from datetime import datetime
import urllib.parse
import hashlib
import uuid

# --- VERİTABANI BAĞLANTISI (GÜÇLENDİRİLDİ) ---
USER = "admin"
PASS = urllib.parse.quote_plus("Hs19051905")
CLUSTER = "cluster0.p1ojawz.mongodb.net"
DB_NAME = "SivasLojistikDB"
CONNECTION_STRING = f"mongodb+srv://{USER}:{PASS}@{CLUSTER}/?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"

def sifre_hashle(sifre):
    if not sifre: return ""
    # Veritabanında zaten hashli bir veri varsa 64 karakterli olacağı için olduğu gibi bırak
    if len(str(sifre)) == 64: return sifre
    return hashlib.sha256(str(sifre).encode()).hexdigest()

@st.cache_resource
def get_db():
    try:
        # tlsCAFile parametresini sertifika hatası almamak için güvenli tutuyoruz
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
    </style>
    """, unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'login' not in st.session_state: st.session_state.update({'login': False, 'role': 'user', 'user': None, 'plaka': None})

# --- GİRİŞ EKRANI ---
if not st.session_state['login']:
    st.title("🚛 Sivas Lojistik")
    if db is not None:
        # Plaka listesini çekerken boş gelme ihtimaline karşı kontrol
        araclar = list(db["Araclar"].find({}, {"plaka": 1}))
        araclar_listesi = [a["plaka"] for a in araclar if "plaka" in a]
        secenekler = ["Plaka Seçiniz...", "⭐ YÖNETİCİ GİRİŞİ"] + araclar_listesi
        secim = st.selectbox("🚛 Giriş Türü / Araç Seçin", secenekler)
        
        kullanici_adi_input = st.text_input("👤 Yönetici Kullanıcı Adı") if secim == "⭐ YÖNETİCİ GİRİŞİ" else ""
        sifre_input = st.text_input("🔑 Şifreniz", type="password")
        
        if st.button("SİSTEME GİRİŞ YAP"):
            hashli_sifre = sifre_hashle(sifre_input)
            if secim == "⭐ YÖNETİCİ GİRİŞİ":
                user_doc = db["Kullanicilar"].find_one({"username": kullanici_adi_input.upper(), "password": hashli_sifre})
                if user_doc and user_doc.get("yetki_seviyesi") in [0, 1]:
                    st.session_state.update({'login': True, 'role': 'admin', 'user': user_doc["username"], 'plaka': 'MERKEZ'})
                    st.rerun()
                else: st.error("❌ Hatalı Giriş Bilgileri!")
            elif secim != "Plaka Seçiniz...":
                arac_doc = db["Araclar"].find_one({"plaka": secim})
                mobil_user = arac_doc.get("mobil_user") if arac_doc else None
                if mobil_user and mobil_user != "YETKİ YOK / GİREMEZ":
                    user_doc = db["Kullanicilar"].find_one({"username": str(mobil_user).upper()})
                    if user_doc and str(user_doc.get("password")) == hashli_sifre:
                        st.session_state.update({'login': True, 'role': 'user', 'plaka': secim, 'user': user_doc["username"]})
                        st.rerun()
                    else: st.error("❌ Hatalı Şifre!")
                else: st.error("❌ Bu aracın atanmış şoförü yok!")

# --- PATRON PANELİ ---
elif st.session_state['role'] == 'admin':
    st.title("📊 Filo Yönetimi")
    if st.button("🔄 Paneli Güncelle"): st.rerun()
    aktif_seferler = list(db["Seferler"].find({"durum": "BEKLEMEDE"}))
    for s in aktif_seferler:
        st.markdown(f'<div class="admin-card"><b>{s["plaka"]}</b> - {s.get("guzergah_detay", "Rota Yok")}</div>', unsafe_allow_html=True)
    if st.sidebar.button("🚪 ÇIKIŞ"): st.session_state['login'] = False; st.rerun()

# --- ŞOFÖR PANELİ ---
else:
    tab1, tab2, tab3 = st.tabs(["📍 SEFER", "⛽ YAKIT", "💰 MASRAF"])
    with tab1:
        # Plaka eşleşmesini .strip() ile boşluklardan arındırarak daha esnek yaptık
        sefer = db["Seferler"].find_one({"plaka": st.session_state['plaka'].strip(), "durum": "BEKLEMEDE"})
        if sefer:
            st.success(f"Aktif Görev: {sefer.get('guzergah_detay')}")
            cikis_km = st.number_input("Depo Çıkış KM", min_value=0.0, step=1.0)
            d_km = st.number_input("Depo Dönüş KM", min_value=0.0, step=1.0)
            if st.button("SEFERİ TAMAMLA"):
                if 0 < cikis_km < d_km:
                    db["Seferler"].update_one({"_id": sefer["_id"]}, {"$set": {"depo_cikis_km": float(cikis_km), "donus_km": float(d_km), "durum": "TAMAMLANDI", "bitis_zamani": datetime.now()}})
                    st.rerun()
                else: st.error("KM değerlerini kontrol edin!")
        else: st.info("Şu an üzerinizde bekleyen sefer yok."); st.button("🔄 Yenile")

    with tab2:
        lt = st.number_input("Litre", min_value=0.0, step=0.01)
        fiyat = st.number_input("Litre Fiyatı", min_value=0.0, step=0.01)
        if st.button("YAKIT KAYDET"):
            db["Giderler"].insert_one({"tarih": datetime.now().strftime("%d/%m/%Y"), "plaka": st.session_state['plaka'], "tur": "YAKIT", "tutar": float(lt*fiyat), "sofor": st.session_state['user'], "kaynak": "MOBIL"})
            st.success("İletildi!")

    with tab3:
        m_tip = st.selectbox("Tür", ["Yemek", "Tamir", "Bakım", "Diğer"])
        m_tutar = st.number_input("Tutar", min_value=0.0)
        if st.button("MASRAFI KAYDET"):
            db["Giderler"].insert_one({"tarih": datetime.now().strftime("%d/%m/%Y"), "plaka": st.session_state['plaka'], "tur": m_tip.upper(), "tutar": float(m_tutar), "sofor": st.session_state['user'], "kaynak": "MOBIL"})
            st.success("İletildi!")

    if st.sidebar.button("🚪 ÇIKIŞ YAP"): st.session_state.update({'login': False}); st.rerun()
