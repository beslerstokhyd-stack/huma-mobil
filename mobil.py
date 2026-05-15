# -*- coding: utf-8 -*-
import streamlit as st
from pymongo import MongoClient
import certifi
from datetime import datetime
import urllib.parse
import pandas as pd

# --- VERİTABANI BAĞLANTISI ---
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
        st.error(f"Veritabanı Bağlantı Hatası: {e}"); return None

db = get_db()

# --- ARAYÜZ TASARIMI (DARK MODE & MOBİL UYUMLU) ---
st.set_page_config(page_title="Sivas Lojistik Mobil", page_icon="🚛", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; background-color: #2ecc71; color: white; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #27ae60; box-shadow: 0px 4px 15px rgba(46, 204, 113, 0.4); }
    .status-box { padding: 20px; border-radius: 15px; background-color: #161b22; border-left: 6px solid #3498db; color: white; margin-bottom: 20px; }
    .calc-box { padding: 20px; border-radius: 15px; background-color: #1e2329; border: 1px solid #2ecc71; text-align: center; margin-top: 15px; }
    .metric-val { color: #2ecc71; font-size: 36px; font-weight: bold; }
    .metric-label { color: #848d97; font-size: 14px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'login' not in st.session_state: st.session_state['login'] = False

# --- GİRİŞ EKRANI ---
if not st.session_state['login']:
    st.title("🚛 Sivas Lojistik")
    st.subheader("Şoför Operasyon Sistemi")
    
    with st.container():
        if db is not None:
            araclar_listesi = [a["plaka"] for a in list(db["Araclar"].find({}, {"plaka": 1}))]
            plaka = st.selectbox("🚛 Aracınızı Seçin", ["Plaka Seçiniz..."] + araclar_listesi)
            sifre = st.text_input("🔑 Şifreniz", type="password")
            
            if st.button("SİSTEME GİRİŞ YAP"):
                arac_doc = db["Araclar"].find_one({"plaka": plaka})
                mobil_user = arac_doc.get("mobil_user") if arac_doc else None
                
                if mobil_user and mobil_user != "YETKİ YOK / GİREMEZ":
                    user_doc = db["Kullanicilar"].find_one({"username": mobil_user})
                    if user_doc and str(user_doc.get("password")) == str(sifre):
                        st.session_state['login'] = True
                        st.session_state['plaka'] = plaka
                        st.session_state['user'] = user_doc.get("username")
                        st.success("Giriş Başarılı! Yönlendiriliyorsunuz...")
                        st.rerun()
                    else: st.error("❌ Hatalı Şifre!")
                else: st.error("❌ Bu araç için mobil erişim yetkisi bulunamadı!")

# --- ANA PANEL ---
else:
    st.sidebar.markdown(f"### 👤 {st.session_state['user']}")
    st.sidebar.markdown(f"### 🆔 {st.session_state['plaka']}")
    st.sidebar.divider()
    
    tab1, tab2, tab3 = st.tabs(["📍 AKTİF SEFER", "⛽ YAKIT ALIMI", "💰 MASRAFLAR"])

    # --- TAB 1: SEFER VE NAVİGASYON ---
    with tab1:
        sefer = db["Seferler"].find_one({"plaka": st.session_state['plaka'], "durum": "BEKLEMEDE"})
        
        if sefer:
            st.markdown(f"""
            <div class="status-box">
                <h2 style='margin:0; color:#3498db;'>Yeni Görev Var!</h2>
                <hr style='border: 0.5px solid #30363d;'>
                <p><b>🚩 Rota:</b> {sefer.get('guzergah_detay')}</p>
                <p><b>📏 Hedef:</b> {sefer.get('plan_km')} KM</p>
                <p><b>⏰ Atama:</b> {sefer.get('tarih')} | {sefer.get('saat')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            duraklar = sefer.get("rota", [])
            if duraklar:
                map_url = f"https://www.google.com/maps/dir/{'/'.join(duraklar)}"
                st.link_button("🗺️ NAVİGASYONU BAŞLAT (GOOGLE HARİTALAR)", map_url)

            st.divider()
            st.write("🏁 **Görevi Sonlandır**")
            d_km = st.number_input("Varış Kilometresi (Kadran Yazısı)", min_value=0.0)
            
            if st.button("SEFERİ TAMAMLA VE KAYDET"):
                if d_km > 0:
                    db["Seferler"].update_one(
                        {"_id": sefer["_id"]}, 
                        {"$set": {"donus_km": d_km, "durum": "TAMAMLANDI", "bitis_zamani": datetime.now()}}
                    )
                    st.balloons()
                    st.success("Veriler merkeze iletildi. İyi istirahatler!")
                    st.rerun()
                else: st.error("Lütfen güncel kilometre bilgisini girin!")
        else:
            st.info("Şu an aktif bir seferiniz bulunmuyor. Merkezden görev bekleniyor...")
            if st.button("🔄 Listeyi Yenile"): st.rerun()

    # --- TAB 2: YAKIT ALIMI (PC PANELİ İLE %100 UYUMLU) ---
    with tab2:
        st.subheader("⛽ Yakıt Alım Bilgisi")
        
        c1, c2 = st.columns(2)
        with c1:
            litre = st.number_input("Alınan Litre (LT)", min_value=0.0, step=0.01, format="%.2f")
        with c2:
            pompa_fiyat = st.number_input("Litre Fiyatı (₺)", min_value=0.0, step=0.01, format="%.2f")
        
        toplam_tutar = round(litre * pompa_fiyat, 2)
        
        st.markdown(f"""
            <div class="calc-box">
                <div class="metric-label">Ödenecek Toplam Tutar</div>
                <div class="metric-val">{toplam_tutar:,.2f} ₺</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        istasyon = st.text_input("📍 İstasyon / Açıklama", placeholder="Örn: Shell - Sivas Merkez")
        
        if st.button("🚀 YAKIT KAYDINI GÖNDER"):
            if litre > 0 and pompa_fiyat > 0:
                yeni_gider = {
                    "gider_id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "tarih": datetime.now().strftime("%d/%m/%Y"), # PC Paneli GG/AA/YYYY formatı bekliyor
                    "plaka": st.session_state['plaka'],
                    "tur": "YAKIT", # PC Paneli "tur" anahtarını ve "YAKIT" değerini bekliyor
                    "tutar": float(toplam_tutar), # PC Paneli "tutar" anahtarını bekliyor
                    "lt": float(litre), # PC Paneli "lt" anahtarını bekliyor
                    "sofor": st.session_state['user'],
                    "kaynak": "MOBIL",
                    "not": istasyon # PC Paneli "not" anahtarını bekliyor
                }
                db["Giderler"].insert_one(yeni_gider)
                st.success("Yakıt kaydı başarıyla merkeze iletildi!")
            else:
                st.error("Lütfen litre ve birim fiyat bilgilerini giriniz!")

    # --- TAB 3: DİĞER MASRAFLAR (PC PANELİ İLE %100 UYUMLU) ---
    with tab3:
        st.subheader("💰 Harcama Bildir")
        # PC Paneli seçenekleri: ["YAKIT", "BAKIM", "TAMİR", "SİGORTA", "LASTİK", "AVANS", "DİĞER"]
        m_tip = st.selectbox("Harcama Türü", ["Yemek", "Tamir", "Bakım", "Lastik", "Avans", "Diğer"])
        m_tutar = st.number_input("Harcama Tutarı (₺)", min_value=0.0)
        m_not = st.text_area("Açıklama (Ne için harcandı?)")
        
        if st.button("✅ MASRAFI SİSTEME İŞLE"):
            if m_tutar > 0:
                yeni_masraf = {
                    "gider_id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "tarih": datetime.now().strftime("%d/%m/%Y"),
                    "plaka": st.session_state['plaka'],
                    "tur": m_tip.upper(), # PC Paneli büyük harf bekler
                    "tutar": float(m_tutar),
                    "lt": 0.0, # Masraflarda litre 0 olmalı
                    "sofor": st.session_state['user'],
                    "kaynak": "MOBIL",
                    "not": m_not
                }
                db["Giderler"].insert_one(yeni_masraf)
                st.success("Harcama kaydı onaya gönderildi.")
            else: st.error("Lütfen tutar giriniz!")

    # ÇIKIŞ BUTONU
    st.sidebar.divider()
    if st.sidebar.button("🚪 SİSTEMDEN ÇIK"):
        st.session_state['login'] = False
        st.rerun()
