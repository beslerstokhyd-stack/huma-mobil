# -*- coding: utf-8 -*-
import streamlit as st
from pymongo import MongoClient
import certifi
from datetime import datetime
import urllib.parse
import hashlib

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
        client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
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
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; background-color: #2ecc71; color: white; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #27ae60; box-shadow: 0px 4px 15px rgba(46, 204, 113, 0.4); }
    .status-box { padding: 20px; border-radius: 15px; background-color: #161b22; border-left: 6px solid #3498db; color: white; margin-bottom: 20px; }
    .admin-card { padding: 15px; border-radius: 10px; background-color: #1e2329; border: 1px solid #3498db; margin-bottom: 10px; }
    .calc-box { padding: 20px; border-radius: 15px; background-color: #1e2329; border: 1px solid #2ecc71; text-align: center; margin-top: 15px; }
    .metric-val { color: #2ecc71; font-size: 30px; font-weight: bold; }
    .metric-label { color: #848d97; font-size: 14px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'login' not in st.session_state: st.session_state['login'] = False
if 'role' not in st.session_state: st.session_state['role'] = 'user'

# --- GİRİŞ EKRANI ---
if not st.session_state['login']:
    st.title("🚛 Sivas Lojistik")
    st.subheader("Mobil Operasyon & Yönetim")
    
    with st.container():
        if db is not None:
            araclar_listesi = [a["plaka"] for a in list(db["Araclar"].find({}, {"plaka": 1}))]
            secenekler = ["Plaka Seçiniz...", "⭐ YÖNETİCİ GİRİŞİ"] + araclar_listesi
            secim = st.selectbox("🚛 Giriş Türü / Araç Seçin", secenekler)
            
            # Yönetici seçildiyse Kullanıcı Adı kutusunu göster
            kullanici_adi_input = ""
            if secim == "⭐ YÖNETİCİ GİRİŞİ":
                kullanici_adi_input = st.text_input("👤 Yönetici Kullanıcı Adı")
            
            sifre_input = st.text_input("🔑 Şifreniz", type="password")
            
            if st.button("SİSTEME GİRİŞ YAP"):
                hashli_sifre = sifre_hashle(sifre_input)
                
                # 1. SENARYO: YÖNETİCİ GİRİŞİ
                if secim == "⭐ YÖNETİCİ GİRİŞİ":
                    if kullanici_adi_input:
                        user_doc = db["Personel"].find_one({
                            "username": kullanici_adi_input.upper(),
                            "password": hashli_sifre,
                            "yetki_seviyesi": {"$in": [0, 1]}
                        })
                        
                        if user_doc:
                            st.session_state['login'] = True
                            st.session_state['role'] = 'admin'
                            st.session_state['user'] = user_doc.get("username")
                            st.session_state['plaka'] = "MERKEZ"
                            st.success(f"Hoş geldiniz, {user_doc.get('username')}")
                            st.rerun()
                        else:
                            st.error("❌ Hatalı Giriş! Bilgileri veya yetkinizi kontrol edin.")
                    else:
                        st.warning("⚠️ Lütfen yönetici kullanıcı adınızı giriniz.")
                
                # 2. SENARYO: ŞOFÖR GİRİŞİ
                elif secim != "Plaka Seçiniz...":
                    arac_doc = db["Araclar"].find_one({"plaka": secim})
                    mobil_user = arac_doc.get("mobil_user") if arac_doc else None
                    
                    if mobil_user and mobil_user != "YETKİ YOK / GİREMEZ":
                        kullanici_adi_buyuk = str(mobil_user).upper()
                        # Şoförler de Personel tablosunda olduğu için oraya bakıyoruz
                        user_doc = db["Personel"].find_one({"username": kullanici_adi_buyuk})
                        
                        if user_doc and str(user_doc.get("password")) == hashli_sifre:
                            st.session_state['login'] = True
                            st.session_state['role'] = 'user'
                            st.session_state['plaka'] = secim
                            st.session_state['user'] = user_doc.get("username")
                            st.rerun()
                        else: st.error("❌ Hatalı Şifre!")
                    else: st.error("❌ Bu araç için mobil erişim yetkisi bulunamadı!")

# --- PATRON / YÖNETİCİ PANELİ ---
elif st.session_state['role'] == 'admin':
    st.sidebar.markdown(f"### 👑 {st.session_state['user']}")
    st.sidebar.info("Yönetici Yetkisi Aktif")
    st.title("📊 Filo Komuta Merkezi")
    
    bugun = datetime.now().strftime("%d/%m/%Y")
    toplam_gider = list(db["Giderler"].aggregate([
        {"$match": {"tarih": bugun}},
        {"$group": {"_id": None, "total": {"$sum": "$tutar"}}}
    ]))
    gider_val = toplam_gider[0]["total"] if toplam_gider else 0
    
    st.markdown(f"""
        <div class="calc-box">
            <div class="metric-label">Bugünkü Saha Gider Toplamı ({bugun})</div>
            <div class="metric-val">{gider_val:,.2f} ₺</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.subheader("🚚 Aktif Araç ve Sefer Durumu")
    aktif_seferler = list(db["Seferler"].find({"durum": "BEKLEMEDE"}))
    
    if aktif_seferler:
        for s in aktif_seferler:
            with st.container():
                st.markdown(f"""
                <div class="admin-card">
                    <b style="color:#3498db; font-size:18px;">{s['plaka']}</b><br>
                    📍 <b>Güzergah:</b> {s.get('guzergah_detay', 'Bilinmiyor')}<br>
                    🕒 <b>Çıkış:</b> {s.get('saat')} | 📏 <b>Hedef:</b> {s.get('plan_km')} KM
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Şu an sahada aktif bir sefer bulunmuyor.")
    
    if st.button("🔄 Paneli Güncelle"): st.rerun()
    st.sidebar.divider()
    if st.sidebar.button("🚪 GÜVENLİ ÇIKIŞ"):
        st.session_state['login'] = False
        st.rerun()

# --- ŞOFÖR PANELİ ---
else:
    st.sidebar.markdown(f"### 👤 {st.session_state['user']}")
    st.sidebar.markdown(f"### 🆔 {st.session_state['plaka']}")
    tab1, tab2, tab3 = st.tabs(["📍 AKTİF SEFER", "⛽ YAKIT ALIMI", "💰 MASRAFLAR"])

    with tab1:
        sefer = db["Seferler"].find_one({"plaka": st.session_state['plaka'], "durum": "BEKLEMEDE"})
        if sefer:
            st.markdown(f"""<div class="status-box"><h2>Yeni Görev!</h2><p><b>🚩 Rota:</b> {sefer.get('guzergah_detay')}</p></div>""", unsafe_allow_html=True)
            duraklar = sefer.get("rota", [])
            if duraklar:
                map_url = f"https://www.google.com/maps/dir/{'/'.join(duraklar)}"
                st.link_button("🗺️ NAVİGASYONU BAŞLAT", map_url)
            st.divider()
            d_km = st.number_input("Varış KM", min_value=0.0)
            if st.button("SEFERİ TAMAMLA"):
                if d_km > 0:
                    db["Seferler"].update_one({"_id": sefer["_id"]}, {"$set": {"donus_km": d_km, "durum": "TAMAMLANDI", "bitis_zamani": datetime.now()}})
                    st.success("Sefer Kapatıldı!"); st.rerun()
        else: st.info("Aktif sefer yok."); st.button("🔄 Yenile")

    with tab2:
        st.subheader("⛽ Yakıt")
        lt = st.number_input("Litre", min_value=0.0, step=0.01)
        fiyat = st.number_input("Litre Fiyatı", min_value=0.0, step=0.01)
        if st.button("YAKIT KAYDINI GÖNDER"):
            db["Giderler"].insert_one({"tarih": datetime.now().strftime("%d/%m/%Y"), "plaka": st.session_state['plaka'], "tur": "YAKIT", "tutar": float(lt*fiyat), "lt": float(lt), "sofor": st.session_state['user'], "kaynak": "MOBIL"})
            st.success("İletildi!")

    with tab3:
        st.subheader("💰 Masraf")
        m_tip = st.selectbox("Tür", ["Yemek", "Tamir", "Bakım", "Diğer"])
        m_tutar = st.number_input("Tutar", min_value=0.0)
        if st.button("MASRAFI KAYDET"):
            db["Giderler"].insert_one({"tarih": datetime.now().strftime("%d/%m/%Y"), "plaka": st.session_state['plaka'], "tur": m_tip.upper(), "tutar": float(m_tutar), "sofor": st.session_state['user'], "kaynak": "MOBIL"})
            st.success("İletildi.")

    if st.sidebar.button("🚪 ÇIKIŞ YAP"):
        st.session_state['login'] = False
        st.rerun()
