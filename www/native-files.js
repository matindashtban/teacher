import { Filesystem, Directory } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';

function toBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error || new Error('خواندن فایل ناموفق بود'));
    reader.onload = () => resolve(String(reader.result).split(',')[1] || '');
    reader.readAsDataURL(blob);
  });
}

window.NativeFiles = {
  async shareFiles(files, title) {
    if (!Array.isArray(files) || !files.length) throw new Error('فایلی برای ذخیره وجود ندارد');
    const saved = [];
    for (const file of files) {
      const safeName = String(file.name || 'export.bin').replace(/[\\/:*?"<>|]/g, '-');
      const base64 = await toBase64(file.blob);
      const result = await Filesystem.writeFile({
        path: `DaftarKelas/${safeName}`,
        data: base64,
        directory: Directory.Cache,
        recursive: true
      });
      saved.push(result.uri);
    }
    await Share.share({
      title: title || files[0].name,
      text: 'فایل خروجی دفتر کلاس',
      files: saved,
      dialogTitle: 'ذخیره یا اشتراک‌گذاری فایل'
    });
    return { success: true, count: saved.length };
  }
};
