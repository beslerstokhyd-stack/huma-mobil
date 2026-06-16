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

# --- OTURUM YÖNETİMİ ---
if 'login' not in st.session_state: st.session_state.update({'login': False, 'role': 'user'})

# --- GİRİŞ EKRANI ---
if not st.session_state['login']:
    st.title("🚛 Sivas Lojistik")
    st.subheader("Mobil Operasyon & Yönetim")
    
    if db is not None:
        araclar_listesi = [a["plaka"] for a in list(db["Araclar"].find({}, {"plaka": 1})) if "plaka" in a]
        secenekler = ["Plaka Seçiniz...", "⭐ YÖNETİCİ GİRİŞİ"] + araclar_listesi
        secim = st.selectbox("🚛 Giriş Türü / Araç Seçin", secenekler)
        
        kullanici_adi_input = st.text_input("👤 Yönetici Kullanıcı Adı") if secim == "⭐ YÖNETİCİ GİRİŞİ" else ""
        sifre_input = st.text_input("🔑 Şifreniz", type="password")
        
        if st.button("SİSTEME GİRİŞ YAP"):
            hashli_sifre = sifre_hashle(sifre_input)
            
            if secim == "⭐ YÖNETİCİ GİRİŞİ":
                user_doc = db["Personel"].find_one({"username": kullanici_adi_input.upper(), "password": hashli_sifre, "yetki_seviyesi": {"$in": [0, 1]}})
                if user_doc:
                    st.session_state.update({'login': True, 'role': 'admin', 'user': user_doc.get("username"), 'plaka': 'MERKEZ'})
                    st.rerun()
                else: st.error("❌ Hatalı Giriş Bilgileri!")
            
            elif secim != "Plaka Seçiniz...":
                arac_doc = db["Araclar"].find_one({"plaka": secim})
                mobil_user = arac_doc.get("mobil_user") if arac_doc else None
                if mobil_user and mobil_user != "YETKİ YOK / GİREMEZ":
                    user_doc = db["Personel"].find_one({"username": str(mobil_user).upper()})
                    if user_doc and str(user_doc.get("password")) == hashli_sifre:
                        st.session_state.update({'login': True, 'role': 'user', 'plaka': secim, 'user': user_doc.get("username")})
                        st.rerun()
                    else: st.error("❌ Hatalı Şifre!")
                else: st.error("❌ Yetki Yok!")

# --- PATRON / YÖNETİCİ PANELİ ---
elif st.session_state['role'] == 'admin':
    st.sidebar.markdown(f"### 👑 {st.session_state['user']}")
    st.title("📊 Filo Komuta Merkezi")
    
    bugun_str = datetime.now().strftime("%d/%m/%Y")
    toplam_gider = list(db["Giderler"].aggregate([{"$match": {"tarih": bugun_str}}, {"$group": {"_id": None, "total": {"$sum": "$tutar"}}}]))
    st.markdown(f'<div class="calc-box"><div class="metric-val">{ (toplam_gider[0]["total"] if toplam_gider else 0):,.2f} ₺</div><div class="metric-label">Bugünkü Saha Gideri</div></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    aktif_seferler = list(db["Seferler"].find({"durum": "BEKLEMEDE"}))
    with col1:
        st.subheader("🚚 Yoldaki")
        for s in aktif_seferler: st.markdown(f'<div class="admin-card"><b>{s["plaka"]}</b><br>📍 {s.get("guzergah_detay")}</div>', unsafe_allow_html=True)
    
    if st.button("🔄 Paneli Güncelle"): st.rerun()
    if st.sidebar.button("🚪 ÇIKIŞ"): st.session_state['login'] = False; st.rerun()

# --- ŞOFÖR PANELİ ---
else:
    st.sidebar.markdown(f"### 👤 {st.session_state['user']}\n### 🆔 {st.session_state['plaka']}")
    tab1, tab2, tab3 = st.tabs(["📍 AKTİF SEFER", "⛽ YAKIT ALIMI", "💰 MASRAFLAR"])
    
    with tab1:
        sefer = db["Seferler"].find_one({"plaka": st.session_state['plaka'], "durum": "BEKLEMEDE"})
        if sefer:
            cikis_km = st.number_input("Depo Çıkış KM", min_value=0.0, step=1.0)
            d_km = st.number_input("Depo Dönüş KM", min_value=0.0, step=1.0)
            if st.button("SEFERİ TAMAMLA"):
                if 0 < cikis_km < d_km:
                    db["Seferler"].update_one({"_id": sefer["_id"]}, {"$set": {"depo_cikis_km": float(cikis_km), "donus_km": float(d_km), "durum": "TAMAMLANDI", "bitis_zamani": datetime.now()}})
                    st.success("Sefer Kapatıldı!"); st.rerun()
                else: st.error("Geçersiz KM!")
        else: st.info("Aktif sefer yok."); st.button("🔄 Yenile")

    with tab2:
        lt = st.number_input("Litre", min_value=0.0, step=0.01)
        fiyat = st.number_input("Litre Fiyatı", min_value=0.0, step=0.01)
        if st.button("YAKIT KAYDINI GÖNDER"):
            if lt > 0:
                db["Giderler"].insert_one({"tarih": datetime.now().strftime("%d/%m/%Y"), "plaka": st.session_state['plaka'], "tur": "YAKIT", "tutar": float(lt*fiyat), "sofor": st.session_state['user'], "kaynak": "MOBIL"})
                st.success("Kayıt iletildi!")

    with tab3:
        m_tip = st.selectbox("Tür", ["Yemek", "Tamir", "Bakım", "Diğer"])
        m_tutar = st.number_input("Tutar", min_value=0.0)
        if st.button("MASRAFI KAYDET"):
            if m_tutar > 0:
                db["Giderler"].insert_one({"tarih": datetime.now().strftime("%d/%m/%Y"), "plaka": st.session_state['plaka'], "tur": m_tip.upper(), "tutar": float(m_tutar), "sofor": st.session_state['user'], "kaynak": "MOBIL"})
                st.success("Masraf iletildi.")

    if st.sidebar.button("🚪 ÇIKIŞ YAP"): st.session_state['login'] = False; st.rerun()
