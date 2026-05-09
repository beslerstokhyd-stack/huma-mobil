import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# Sayfa Yapılandırması
st.set_page_config(page_title="Hüma Lojistik Mobil", page_icon="🚚")

# MongoDB Bağlantısı (Senin Cluster Bilgilerin)
client = MongoClient("mongodb+srv://beslerstokhyd:Asdfgh123.@cluster0.v8v6f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["HumaLojistik"]

# GİRİŞ SİSTEMİ
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🚚 Hüma Lojistik Giriş")
    
    # Kullanıcı adını Personel Yönetimi'ndeki 'username' ile eşleştiriyoruz
    user_input = st.text_input("Kullanıcı Adı (HYDSNL vb.)")
    sifre_input = st.text_input("Şifre", type="password")
    
    if st.button("Giriş Yap"):
        # Veritabanından kullanıcıyı ve şifreyi sorguluyoruz
        kullanici_kaydi = db["Kullanicilar"].find_one({
            "username": user_input,
            "password": sifre_input
        })
        
        if kullanici_kaydi:
            # Personel bilgilerinden plakasını çekiyoruz
            personel_detay = db["Personel"].find_one({"username": user_input})
            
            st.session_state['logged_in'] = True
            st.session_state['user_name'] = user_input
            # Eğer plaka atanmamışsa 'BOŞTA' kabul ediyoruz
            st.session_state['plaka'] = personel_detay.get("atanan_plaka", "BOŞTA") if personel_detay else "BOŞTA"
            st.success("Giriş Başarılı!")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı!")

else:
    # ANA UYGULAMA PANELİ
    plaka = st.session_state['plaka']
    
    # Sol Menü / Çıkış
    with st.sidebar:
        st.success(f"Giriş: {st.session_state['user_name']}")
        st.write(f"🚚 Araç: {plaka}")
        if st.button("Güvenli Çıkış"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.title(f"🚚 {plaka}")
    
    tab1, tab2, tab3 = st.tabs(["📍 SEFER TAKİBİ", "⛽ YAKIT ALIMI", "💰 MASRAF YAZ"])

    with tab1:
        st.subheader("Sefer Kilometre Takibi")
        
        # 'BEKLEMEDE' dahil tüm aktif durumları sorguluyoruz
        aktif_sefer = db["Seferler"].find_one({
            "plaka": {"$regex": plaka.replace(" ", ""), "$options": "i"},
            "durum": {"$in": ["BEKLEYOR", "BEKLEMEDE", "AKTİF", "YOLDA"]}
        })

        if aktif_sefer and plaka != "BOŞTA":
            st.info(f"✅ Aktif Sefer: {aktif_sefer.get('sefer_no', 'N/A')}")
            st.write(f"📅 Tarih: {aktif_sefer.get('tarih', '')}")
            st.write(f"🗺️ Güzergah: {aktif_sefer.get('guzergah', 'Belirtilmedi')}")
            
            # KM Güncelleme Alanı
            yeni_km = st.number_input("Güncel Kilometre Yazınız", min_value=0)
            if st.button("KM GÜNCELLE"):
                db["Seferler"].update_one(
                    {"_id": aktif_sefer["_id"]},
                    {"$set": {"fiili_km": yeni_km, "son_guncelleme": datetime.now()}}
                )
                st.success("Kilometre başarıyla güncellendi.")
        else:
            st.warning("⚠️ Üzerinize tanımlı aktif bir sefer bulunamadı veya aracınız 'BOŞTA'.")

    with tab2:
        st.subheader("⛽ Yakıt Bilgisi Girişi")
        y_litre = st.number_input("Kaç Litre Alındı?", min_value=0.0)
        y_tutar = st.number_input("Toplam Tutar (₺)", min_value=0.0)
        
        if st.button("YAKITI KAYDET"):
            db["Yakitlar"].insert_one({
                "tarih": datetime.now(),
                "plaka": plaka,
                "sofor": st.session_state['user_name'],
                "litre": y_litre,
                "tutar": y_tutar
            })
            st.success("Yakıt bilgisi kaydedildi.")

    with tab3:
        st.subheader("💰 Harcama ve Masraf")
        m_tip = st.selectbox("Masraf Türü", ["Yemek", "Tamir", "Otoyol / Köprü", "AdBlue", "Lastik", "Avans", "Park / Yıkama", "DİĞER"])
        m_tutar = st.number_input("Harcama Tutarı (₺)", min_value=0.0)
        m_aciklama = st.text_area("Masraf Açıklaması")
        
        if st.button("MASRAFI KAYDET"):
            if m_tutar > 0:
                db["Giderler"].insert_one({
                    "tarih": datetime.now(),
                    "plaka": plaka,
                    "sofor": st.session_state['user_name'],
                    "kategori": m_tip,
                    "tutar": m_tutar,
                    "aciklama": m_aciklama,
                    "kaynak": "MOBIL"
                })
                st.success("Masraf merkeze iletildi.")