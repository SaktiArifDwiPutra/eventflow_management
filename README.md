# EventFlow Management

Modul kustom Odoo 19 untuk mengelola event dan pelatihan: pengajuan dan persetujuan event, pendaftaran peserta, check-in, tiket, laporan, dan halaman pendaftaran publik. Modul ini memperluas fitur standar Odoo (Events, Sales, Website) dan tidak menggantinya.

Dependensi: `event`, `event_sale`, `website_event`.

## Fitur

**Persetujuan event**
- Alur status: Draft → Submitted → Approved atau Rejected, dan Approved → Cancelled.
- Menolak event wajib menyertakan alasan. Membatalkan event juga wajib menyertakan alasan.
- Setelah Approved, nama, tanggal, dan kuota kursi terkunci. Untuk mengubahnya, Manager harus me-Reset event ke Draft.
- Event yang sudah Cancelled tidak bisa dikembalikan ke Draft.

**Pendaftaran dan check-in**
- Pendaftaran peserta hanya bisa dibuat untuk event yang sudah Approved, termasuk lewat Sales dan website.
- Saat event dibatalkan, pendaftaran peserta yang belum hadir ikut dibatalkan otomatis.
- Check-in (status Attended) hanya bisa dilakukan oleh Event Staff ke atas, hanya mulai hari pertama event sampai event berakhir, dan untuk pesanan berbayar hanya setelah fakturnya lunas. Tiket gratis boleh langsung check-in.
- Setiap check-in mencatat siapa yang melakukannya (Checked In By).

**Notifikasi**
- Saat event di-Submit, setiap Manager mendapat tugas (activity) "Approval needed".
- Pengaju event diberi tahu saat event di-Approve, di-Reject (beserta alasan), atau dibatalkan.
- Tindakan terjadwal harian: Manager mendapat tugas "No attendance recorded" untuk event Approved yang berakhir dalam 7 hari terakhir, punya pendaftaran, tapi belum ada peserta yang ditandai hadir.

**Website publik**
- Event tampil di `/event` hanya setelah Approved, dan otomatis disembunyikan saat Rejected, Cancelled, atau di-Reset ke Draft.
- Event yang belum Approved tidak bisa dipublikasikan secara manual.

**Laporan dan tampilan**
- Daftar event menampilkan Approval Status, jumlah peserta, jumlah hadir, dan persentase kehadiran.
- Filter pencarian: Pending Approval, Approved, Cancelled, dan pengelompokan per Approval Status.
- Menu Event Dashboard (papan kanban per status).
- Menu Pending Approval untuk Manager.
- Reporting: Approval Overview, Attendance Report, dan Revenue Report (penjualan dan jumlah yang sudah ditagihkan per event, belum sampai tahap dibayar).
- Cetak Attendance List (PDF daftar hadir dengan kolom tanda tangan) dari menu Print di form event.
- Tiket PDF dengan desain sendiri (QR code, data peserta, lokasi, waktu).

## Peran dan hak akses

Tiga group dibuat oleh modul ini, dan masing-masing mewarisi group di bawahnya:

| Group | Bisa melakukan |
|---|---|
| EventFlow: Event Staff | Membuat event, Submit, Reset event yang Rejected, check-in peserta |
| EventFlow: Event Manager | Semua milik Staff, ditambah Approve, Reject, Cancel, Reset event Approved, menu Pending Approval dan semua laporan |
| EventFlow: Event Administrator | Semua milik Manager, ditambah hak Administrator bawaan modul Events |

Pembatasan data:
- Staff hanya melihat event yang Approved atau Cancelled, atau yang ia buat atau ajukan sendiri. Daftar peserta mengikuti aturan yang sama.
- Manager dan Administrator melihat semua event dan peserta.

Cara memasang group ke user: **Settings → Users & Companies → Groups**, hapus filter Internal Groups, cari `EventFlow`, buka group-nya, lalu tambahkan user di tab Users. Group ini tidak tampil di tab Access Rights pada form user.

## Cara penggunaan

1. **Staff** membuat event di aplikasi Events, mengisi tiket di tab Tickets, lalu klik **Submit for Approval**.
2. **Manager** membuka menu **Events → Pending Approval**, memeriksa event, lalu klik **Approve** (event langsung tampil di website) atau mengisi Rejection Reason dan klik **Reject**.
3. Jika ditolak, **Staff** memperbaiki event, klik **Reset to Draft**, lalu Submit lagi.
4. Peserta mendaftar lewat `/event` di website atau lewat Sales Order.
5. Pada hari event, **Staff** menandai peserta sebagai **Attended** (lewat daftar peserta atau menu Registration Desk).
6. Jika event harus dibatalkan, **Manager** mengisi Cancel Reason di event Approved lalu klik **Cancel Event**.
7. Manager memantau lewat Event Dashboard dan menu Reporting.

## Instalasi dan pengembangan (Docker)

Folder modul di-mount ke container Odoo sebagai `/mnt/extra-addons`. Setelah mengubah kode:

```bash
# update modul
docker compose exec odoo odoo -d eventflow_dev -u eventflow_management \
  --stop-after-init --db_host=db --db_user=odoo --db_password=odoo
docker compose restart odoo
```

Menjalankan tes otomatis (jalankan setiap kali mengubah aturan bisnis):

```bash
docker compose exec odoo odoo -d eventflow_dev -u eventflow_management \
  --test-enable --test-tags /eventflow_management --http-port=8072 \
  --stop-after-init --db_host=db --db_user=odoo --db_password=odoo
```

Hasil yang diharapkan: `0 failed, 0 error(s)`. Port `8072` dipakai agar tidak bentrok dengan server Odoo yang sedang berjalan.

## Catatan konfigurasi dan batasan

- **Laporan PDF di Docker.** Buat System Parameter `report.url` dengan nilai `http://localhost:8069` (port di dalam container). Tanpa itu CSS tidak termuat dan PDF bawaan Odoo tampil polos. Pengaturan ini tersimpan di database, bukan di kode.
- **Notifikasi.** Agar pesan masuk ke Inbox dan tidak dikirim lewat email, ubah preferensi user ke "Handle in Odoo". Di lingkungan lokal tanpa mail server, notifikasi email akan gagal.
- **Pembayaran tiket.** Untuk uji coba, aktifkan penyedia pembayaran Demo (`payment_demo`). Penyedia sungguhan seperti Stripe atau Xendit butuh akun dan kunci API.
- **Pembatalan event** tidak membatalkan Sales Order maupun faktur. Pengembalian dana dilakukan manual lewat Invoicing.
- **Revenue Report** menampilkan jumlah yang ditagihkan, bukan jumlah yang sudah dibayar.
- Tab Shop di website dan produk demo diatur lewat database, jadi perlu diulang di database baru.