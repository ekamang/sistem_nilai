import streamlit as st
import pandas as pd
import sqlite3

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Nilai Siswa", 
    page_icon="📚",
    layout="wide"
)

# --- KONEKSI DATABASE (SQLite) ---
conn = sqlite3.connect("database_siswa.db", check_same_thread=False)
cursor = conn.cursor()

# Buat tabel jika belum ada
cursor.execute('''
    CREATE TABLE IF NOT EXISTS siswa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nis TEXT UNIQUE,
        nama TEXT,
        kelas TEXT,
        mapel TEXT,
        nilai_1 REAL DEFAULT 0,
        nilai_2 REAL DEFAULT 0,
        nilai_3 REAL DEFAULT 0,
        nilai_4 REAL DEFAULT 0
    )
''')
conn.commit()

# Migrasi kolom lama jika ada
for col in ['nilai_1', 'nilai_2', 'nilai_3', 'nilai_4']:
    try:
        cursor.execute(f"ALTER TABLE siswa ADD COLUMN {col} REAL DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass

st.title("📚 Sistem Pengelolaan Nilai Siswa")

# Menu Navigasi Samping (Teks Dibuat Konsisten)
MENU_INPUT = "📝 Input Nilai Sekelas"
MENU_EDIT = "✏️ Edit Nilai Per Siswa"
MENU_REKAP = "📊 Rekap & Filter Data"
MENU_IMPORT = "📁 Import Data Master (Excel)"
MENU_KELOLA = "⚙️ Kelola / Hapus Siswa"

menu = st.sidebar.selectbox("📱 Pilih Menu", [
    MENU_INPUT, 
    MENU_EDIT,
    MENU_REKAP, 
    MENU_IMPORT,
    MENU_KELOLA
])

# --- MENU 1: INPUT NILAI SEKELAS (TABEL MENYAMPING) ---
if menu == MENU_INPUT:
    st.subheader("📝 Input Nilai Sekelas (Tampilan Tabel)")
    
    df = pd.read_sql_query("SELECT * FROM siswa", conn)
    
    if df.empty:
        st.warning("Belum ada data siswa. Silakan lakukan 'Import Data Master' terlebih dahulu.")
    else:
        col_k, col_s = st.columns(2)
        with col_k:
            daftar_kelas = sorted(list(df['kelas'].unique()))
            pilih_kelas = st.selectbox("🏫 Pilih Kelas:", daftar_kelas)
        
        with col_s:
            pilih_sesi = st.selectbox("📅 Pilih Sesi Nilai yang Ingin Diisi:", [
                "Nilai 1 (Tugas / PH 1)",
                "Nilai 2 (Tugas / PH 2)",
                "Nilai 3 (Tugas / PH 3)",
                "Nilai 4 (Tugas / PH 4)"
            ])
            
        map_kolom = {
            "Nilai 1 (Tugas / PH 1)": "nilai_1",
            "Nilai 2 (Tugas / PH 2)": "nilai_2",
            "Nilai 3 (Tugas / PH 3)": "nilai_3",
            "Nilai 4 (Tugas / PH 4)": "nilai_4"
        }
        kolom_db = map_kolom[pilih_sesi]
        
        df_kelas = df[df['kelas'] == pilih_kelas].sort_values(by='nama').reset_index(drop=True)
        
        st.info(f"Mengisi **{pilih_sesi}** untuk **Kelas {pilih_kelas}** ({len(df_kelas)} Siswa)")
        
        # Header Tabel
        h1, h2, h3, h4 = st.columns([1, 2.5, 3, 2.5])
        with h1:
            st.markdown("**No**")
        with h2:
            st.markdown("**NIS**")
        with h3:
            st.markdown("**Nama Siswa**")
        with h4:
            st.markdown(f"**{pilih_sesi}**")
            
        st.divider()
        
        inputs = {}
        with st.form("form_input_sekelas"):
            for idx, row in df_kelas.iterrows():
                c1, c2, c3, c4 = st.columns([1, 2.5, 3, 2.5])
                val_db = float(row.get(kolom_db, 0) or 0)
                val_str = "" if val_db == 0 else str(int(round(val_db)))
                
                with c1:
                    st.write(f"**{idx + 1}**")
                with c2:
                    st.write(str(row['nis']))
                with c3:
                    st.write(str(row['nama']))
                with c4:
                    inputs[row['id']] = st.text_input(
                        label=f"nilai_{row['id']}", 
                        value=val_str, 
                        key=f"in_{row['id']}", 
                        label_visibility="collapsed",
                        placeholder="0"
                    )
            
            st.divider()
            simpan_sekelas = st.form_submit_button("💾 Simpan Semua Nilai Kelas Ini", use_container_width=True)
            
            if simpan_sekelas:
                for student_id, val_text in inputs.items():
                    val_clean = val_text.replace(',', '.').strip()
                    if val_clean == "":
                        val_fix = 0.0
                    else:
                        try:
                            val_fix = float(val_clean)
                        except ValueError:
                            val_fix = 0.0
                    
                    cursor.execute(f'''
                        UPDATE siswa 
                        SET {kolom_db} = ?
                        WHERE id = ?
                    ''', (val_fix, int(student_id)))
                conn.commit()
                st.success(f"Berhasil menyimpan seluruh {pilih_sesi} untuk Kelas {pilih_kelas}!")

# --- MENU 2: EDIT NILAI PER SISWA ---
elif menu == MENU_EDIT:
    st.subheader("✏️ Edit & Koreksi Nilai Siswa")
    
    df = pd.read_sql_query("SELECT * FROM siswa", conn)
    
    if df.empty:
        st.info("Belum ada data siswa di database.")
    else:
        daftar_kelas = sorted(list(df['kelas'].unique()))
        pilih_kelas = st.selectbox("🏫 Pilih Kelas:", daftar_kelas, key="edit_kelas")
        
        df_kelas = df[df['kelas'] == pilih_kelas].sort_values(by='nama')
        
        if df_kelas.empty:
            st.warning("Tidak ada data siswa di kelas ini.")
        else:
            pilih_siswa = st.selectbox(
                "👤 Pilih Nama Siswa yang Ingin Diedit:", 
                df_kelas.apply(lambda x: f"{x['nama']} (NIS: {x['nis']})", axis=1),
                key="edit_siswa"
            )
            
            nama_saja = pilih_siswa.split(" (NIS:")[0]
            data_siswa = df_kelas[df_kelas['nama'] == nama_saja].iloc[0]
            
            st.markdown(f"### Siswa: **{data_siswa['nama']}**")
            st.caption(f"NIS: {data_siswa['nis']} | Kelas: {data_siswa['kelas']}")
            
            with st.form("form_edit_semua_nilai"):
                col1, col2 = st.columns(2)
                with col1:
                    n1 = st.text_input("Nilai 1:", value=str(int(round(data_siswa.get('nilai_1', 0) or 0))))
                    n2 = st.text_input("Nilai 2:", value=str(int(round(data_siswa.get('nilai_2', 0) or 0))))
                with col2:
                    n3 = st.text_input("Nilai 3:", value=str(int(round(data_siswa.get('nilai_3', 0) or 0))))
                    n4 = st.text_input("Nilai 4:", value=str(int(round(data_siswa.get('nilai_4', 0) or 0))))
                    
                simpan_edit = st.form_submit_button("💾 Perbarui Semua Nilai")
                if simpan_edit:
                    try:
                        v1 = float(n1.replace(',', '.'))
                        v2 = float(n2.replace(',', '.'))
                        v3 = float(n3.replace(',', '.'))
                        v4 = float(n4.replace(',', '.'))
                        
                        cursor.execute('''
                            UPDATE siswa 
                            SET nilai_1=?, nilai_2=?, nilai_3=?, nilai_4=?
                            WHERE id=?
                        ''', (v1, v2, v3, v4, int(data_siswa['id'])))
                        conn.commit()
                        st.success(f"Nilai untuk {data_siswa['nama']} berhasil diperbarui!")
                    except ValueError:
                        st.error("Mohon pastikan semua kolom nilai diisi dengan angka yang valid!")

# --- MENU 3: REKAP & FILTER DATA ---
elif menu == MENU_REKAP:
    st.subheader("📋 Rekapitulasi Data Nilai")
    
    df = pd.read_sql_query("SELECT * FROM siswa", conn)
    
    if not df.empty:
        df['nilai_1'] = df['nilai_1'].fillna(0)
        df['nilai_2'] = df['nilai_2'].fillna(0)
        df['nilai_3'] = df['nilai_3'].fillna(0)
        df['nilai_4'] = df['nilai_4'].fillna(0)
        
        df['rata_rata'] = ((df['nilai_1'] + df['nilai_2'] + df['nilai_3'] + df['nilai_4']) / 4).round(0).astype(int)
        
        cari_nama = st.text_input("🔍 Cari Nama / NIS:")
        daftar_kelas = ["Semua Kelas"] + sorted(list(df['kelas'].unique()))
        pilih_kelas = st.selectbox("🏫 Filter Kelas:", daftar_kelas)
        
        df_filtered = df.copy()
        if cari_nama:
            df_filtered = df_filtered[
                df_filtered['nama'].astype(str).str.contains(cari_nama, case=False, na=False) | 
                df_filtered['nis'].astype(str).str.contains(cari_nama, case=False, na=False)
            ]
        if pilih_kelas != "Semua Kelas":
            df_filtered = df_filtered[df_filtered['kelas'] == pilih_kelas]
            
        tampilan_df = df_filtered[['nis', 'nama', 'kelas', 'mapel', 'nilai_1', 'nilai_2', 'nilai_3', 'nilai_4', 'rata_rata']]
        
        st.dataframe(tampilan_df, use_container_width=True)
        
        st.download_button(
            label="📥 Unduh Rekap ke Excel / CSV",
            data=tampilan_df.to_csv(index=False).encode('utf-8'),
            file_name="rekap_nilai_siswa.csv",
            mime="text/csv"
        )
    else:
        st.info("Belum ada data di database.")

# --- MENU 4: IMPORT DATA MASTER DARI EXCEL ---
elif menu == MENU_IMPORT:
    st.subheader("📁 Import Master Excel")
    st.caption("Unggah file Excel berisi kolom: nis, nama, kelas, mapel.")
    
    uploaded_file = st.file_uploader("Unggah file Excel (.xlsx) / CSV", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                try:
                    df_excel = pd.read_csv(uploaded_file, sep=None, engine='python')
                except Exception:
                    uploaded_file.seek(0)
                    df_excel = pd.read_csv(uploaded_file, sep=';')
            else:
                df_excel = pd.read_excel(uploaded_file)
            
            df_excel.columns = df_excel.columns.str.strip().str.lower()
            
            rename_map = {
                'nilai 1': 'nilai_1', 'nilai1': 'nilai_1',
                'nilai 2': 'nilai_2', 'nilai2': 'nilai_2',
                'nilai 3': 'nilai_3', 'nilai3': 'nilai_3',
                'nilai 4': 'nilai_4', 'nilai4': 'nilai_4'
            }
            df_excel.rename(columns=rename_map, inplace=True)
            
            if 'mapel' not in df_excel.columns:
                df_excel['mapel'] = 'INFORMATIKA'
            for col in ['nilai_1', 'nilai_2', 'nilai_3', 'nilai_4']:
                if col not in df_excel.columns:
                    df_excel[col] = 0.0
                else:
                    df_excel[col] = pd.to_numeric(df_excel[col], errors='coerce').fillna(0.0)
            
            st.dataframe(df_excel.head())
            
            if st.button("Simpan Master ke Database"):
                for index, row in df_excel.iterrows():
                    cursor.execute('''
                        INSERT OR REPLACE INTO siswa (nis, nama, kelas, mapel, nilai_1, nilai_2, nilai_3, nilai_4) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(row['nis']), 
                        str(row['nama']), 
                        str(row['kelas']), 
                        str(row['mapel']), 
                        float(row['nilai_1']),
                        float(row['nilai_2']),
                        float(row['nilai_3']),
                        float(row['nilai_4'])
                    ))
                conn.commit()
                st.success("Data master berhasil disimpan!")
        except Exception as e:
            st.error(f"Gagal memproses file: {e}")

# --- MENU 5: KELOLA / HAPUS SISWA ---
elif menu == MENU_KELOLA:
    st.subheader("⚙️ Kelola Siswa Manual")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ➕ Tambah Siswa Baru")
        with st.form("form_tambah_manual"):
            nis_baru = st.text_input("NIS / NISN:")
            nama_baru = st.text_input("Nama Lengkap:")
            kelas_baru = st.text_input("Kelas (Contoh: XII.1):")
            mapel_baru = st.text_input("Mata Pelajaran:", value="INFORMATIKA")
            
            simpan_siswa = st.form_submit_button("➕ Simpan Siswa")
            if simpan_siswa:
                if nis_baru and nama_baru and kelas_baru:
                    try:
                        cursor.execute('''
                            INSERT INTO siswa (nis, nama, kelas, mapel, nilai_1, nilai_2, nilai_3, nilai_4)
                            VALUES (?, ?, ?, ?, 0, 0, 0, 0)
                        ''', (nis_baru, nama_baru, kelas_baru, mapel_baru))
                        conn.commit()
                        st.success(f"Siswa baru **{nama_baru}** berhasil ditambahkan!")
                    except sqlite3.IntegrityError:
                        st.error("NIS sudah terdaftar!")
                else:
                    st.warning("Lengkapi NIS, Nama, dan Kelas!")

    with col2:
        st.markdown("### 🗑️ Hapus Siswa")
        df = pd.read_sql_query("SELECT * FROM siswa", conn)
        
        if not df.empty:
            pilih_id = st.selectbox("Pilih Siswa yang Ingin Dihapus:", 
                                    df.apply(lambda x: f"ID: {x['id']} | {x['nama']} - Kelas {x['kelas']}", axis=1))
            id_terpilih = int(pilih_id.split(" | ")[0].replace("ID: ", ""))
            
            if st.button("❌ Hapus Siswa Ini"):
                cursor.execute("DELETE FROM siswa WHERE id=?", (id_terpilih,))
                conn.commit()
                st.success("Siswa berhasil dihapus!")
        else:
            st.info("Belum ada data siswa.")