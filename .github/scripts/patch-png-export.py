from pathlib import Path
import json
root = Path('.')
candidates = []
for candidate in root.rglob('*.jsx'):
    try:
        candidate_text = candidate.read_text(encoding='utf-8')
    except Exception:
        continue
    if 'exportAttendanceImage' in candidate_text and 'saveOrSharePng' in candidate_text:
        candidates.append((candidate, candidate_text))
if not candidates:
    raise SystemExit('Could not locate the app JSX file containing PNG export functions. Files: ' + ', '.join(str(p) for p in root.rglob('*.jsx')))
main, s = candidates[0]
project_root = main.parent.parent
changes = 0
def replace(old, new, label):
    global s, changes
    if old not in s:
        raise SystemExit(f'Could not find expected source block: {label}')
    s = s.replace(old, new, 1)
    changes += 1
replace("import { jsPDF } from 'jspdf';", "import { jsPDF } from 'jspdf';\nimport { Capacitor } from '@capacitor/core';\nimport { Filesystem, Directory } from '@capacitor/filesystem';\nimport { Share } from '@capacitor/share';", 'plugin imports')
replace("""            // خروجی تصویری (PNG) از لیست حضور همان روز، بدون نیاز به کتابخانه خارجی
            const exportAttendanceImage = () => {""", """            // خروجی تصویری (PNG) از لیست حضور همان روز
            const exportAttendanceImage = async () => {""", 'attendance function')
replace("""                c.toBlob(blob => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url; a.download = `حضور-${date}.png`;
                    document.body.appendChild(a); a.click(); a.remove();
                    setTimeout(() => URL.revokeObjectURL(url), 2000);
                }, 'image/png');""", """                const blob = await new Promise(resolve => c.toBlob(resolve, 'image/png'));
                if (!blob) throw new Error('ساخت PNG ناموفق بود');
                const result = await saveOrSharePng(blob, `حضور-${date}.png`, 'لیست حضور و غیاب');
                if (result !== 'cancelled') showToast(result === 'shared' ? '📤 تصویر حضور برای اشتراک آماده شد' : '📥 تصویر حضور ساخته شد');""", 'attendance export')
replace("onClick: exportAttendanceImage }, '📷 تصویر لیست (PNG)'", "onClick: () => exportAttendanceImage().catch(e => { console.error(e); showToast('خطا در ساخت یا اشتراک PNG: ' + (e.message || ''), 'error'); }) }, '📷 تصویر لیست (PNG)'", 'attendance click handler')
replace("""        async function saveOrSharePng(blob, filename, title) {
            try {
                if (typeof File !== 'undefined' && navigator.share && navigator.canShare) {
                    const file = new File([blob], filename, { type: 'image/png' });
                    if (navigator.canShare({ files: [file] })) {
                        await navigator.share({ files: [file], title: title || filename });
                        return 'shared';
                    }
                }
            } catch (e) {
                if (e && e.name === 'AbortError') return 'cancelled';
                console.warn('share unavailable; falling back to download', e);
            }
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = filename;
            document.body.appendChild(a); a.click(); a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 2500);
            return 'downloaded';
        }""", """        async function saveOrSharePng(blob, filename, title) {
            // Android WebView دانلود با لینک blob را به‌درستی انجام نمی‌دهد؛
            // بنابراین در APK فایل واقعی را در حافظه موقت می‌نویسیم و با Share
            // بومی اندروید به واتساپ، تلگرام و سایر برنامه‌ها می‌فرستیم.
            if (Capacitor.isNativePlatform()) {
                const safeName = String(filename || 'image.png').replace(/[\\\\/:*?\\\"<>|]/g, '-');
                const base64 = await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(String(reader.result).split(',')[1] || '');
                    reader.onerror = () => reject(reader.error || new Error('خواندن تصویر ناموفق بود'));
                    reader.readAsDataURL(blob);
                });
                const path = `shared-images/${Date.now()}-${safeName}`;
                const saved = await Filesystem.writeFile({ path, data: base64, directory: Directory.Cache, recursive: true });
                try {
                    await Share.share({ title: title || safeName, text: title || '', files: [saved.uri], dialogTitle: 'اشتراک‌گذاری تصویر PNG' });
                    return 'shared';
                } catch (e) {
                    if (e && (e.message || '').toLowerCase().includes('cancel')) return 'cancelled';
                    throw e;
                }
            }
            try {
                if (typeof File !== 'undefined' && navigator.share && navigator.canShare) {
                    const file = new File([blob], filename, { type: 'image/png' });
                    if (navigator.canShare({ files: [file] })) {
                        await navigator.share({ files: [file], title: title || filename });
                        return 'shared';
                    }
                }
            } catch (e) {
                if (e && e.name === 'AbortError') return 'cancelled';
                console.warn('share unavailable; falling back to download', e);
            }
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = filename;
            document.body.appendChild(a); a.click(); a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 10000);
            return 'downloaded';
        }""", 'native PNG share helper')
main.write_text(s, encoding='utf-8')
pkg = project_root / 'package.json'
data = json.loads(pkg.read_text(encoding='utf-8'))
data['dependencies']['@capacitor/filesystem'] = '7.1.4'
data['dependencies']['@capacitor/share'] = '7.0.2'
pkg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')
print(f'Applied {changes} PNG compatibility fixes and added Capacitor Filesystem/Share.')
