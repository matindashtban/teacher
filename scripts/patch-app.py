from pathlib import Path
import re

p = Path("www/index.html")
s = p.read_text(encoding="utf-8")

old = """        async function saveOrSharePngs(files, title) {
            try {
                if (typeof File !== 'undefined' && navigator.share && navigator.canShare) {
                    const list = files.map(f => new File([f.blob], f.name, { type: 'image/png' }));
                    if (navigator.canShare({ files: list })) { await navigator.share({ files: list, title: title || files[0].name }); return 'shared'; }
                }
            } catch (e) {
                if (e && e.name === 'AbortError') return 'cancelled';
                console.warn('share unavailable; falling back to download', e);
            }
            files.forEach((f, i) => setTimeout(() => attDownload(f.blob, f.name), i * 450));
            return 'downloaded';
        }
"""
new = """        async function saveOrSharePngs(files, title) {
            try {
                if (window.NativeFiles && window.NativeFiles.shareFiles) {
                    await window.NativeFiles.shareFiles(files.map(f => ({ blob: f.blob, name: f.name, mimeType: 'image/png' })), title || files[0].name);
                    return 'shared';
                }
                if (typeof File !== 'undefined' && navigator.share && navigator.canShare) {
                    const list = files.map(f => new File([f.blob], f.name, { type: 'image/png' }));
                    if (navigator.canShare({ files: list })) { await navigator.share({ files: list, title: title || files[0].name }); return 'shared'; }
                }
            } catch (e) {
                if (e && e.name === 'AbortError') return 'cancelled';
                console.error('native share failed', e);
                throw e;
            }
            files.forEach((f, i) => setTimeout(() => attDownload(f.blob, f.name), i * 450));
            return 'downloaded';
        }
"""
assert old in s, "PNG exporter function not found"
s = s.replace(old, new, 1)

start = s.index("            const exportBackup = () => {")
end = s.index("\n\n            const triggerImport", start)
backup = """            const exportBackup = async () => {
                try {
                    const filename = `backup-daftar-kelas-${todayISO()}.json`;
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    if (window.NativeFiles && window.NativeFiles.shareFiles) {
                        await window.NativeFiles.shareFiles([{ blob, name: filename, mimeType: 'application/json' }], 'پشتیبان دفتر کلاس');
                    } else if (typeof File !== 'undefined' && navigator.share && navigator.canShare) {
                        const file = new File([blob], filename, { type: 'application/json' });
                        if (navigator.canShare({ files: [file] })) await navigator.share({ files: [file], title: 'پشتیبان دفتر کلاس' });
                        else attDownload(blob, filename);
                    } else {
                        attDownload(blob, filename);
                    }
                    showToast('📤 فایل پشتیبان آماده‌ی ذخیره یا اشتراک‌گذاری است');
                    save({ ...data, meta: { ...(data.meta || {}), lastBackupAt: new Date().toISOString() } });
                } catch (e) {
                    if (e && e.name === 'AbortError') return;
                    console.error('export error', e);
                    showToast('⚠️ ساخت یا ارسال فایل بکاپ ناموفق بود', 'error');
                }
            };"""
s = s[:start] + backup + s[end:]

s = s.replace("{ key: 'aboutMe', label: '🙋 درباره من' },", "{ key: 'aboutMe', label: '🏫 اطلاعات مدرسه و معلم' },", 1)
s = s.replace("onLogout && React.createElement('button', { onClick: onLogout, className: 'btn-ghost text-small', style: { padding: '6px 10px', borderRadius: 10, fontSize: 12, cursor: 'pointer' } }, 'خروج از حساب')",
              "onLogout && React.createElement('button', { onClick: () => window.alert('ساخته شده با ❤ توسط متین دشتبان برای معلمان دلسوز ایران زمین\\n\\ntelegram: @matindashtban'), className: 'btn-ghost text-small', style: { padding: '6px 10px', borderRadius: 10, fontSize: 12, cursor: 'pointer' } }, 'درباره سازنده')", 1)

about = re.compile(r"        function AboutMe\(\{ data, save \}\) \{.*?\n        \}\n\n        function TeacherApp", re.S)
about_new = """        function AboutMe({ data, save }) {
            const meta = data.meta || {};
            const [school, setSchool] = React.useState(meta.schoolName || '');
            const [teacher, setTeacher] = React.useState(meta.teacherName || '');
            const saveInfo = () => save({ ...data, meta: { ...(data.meta || {}), schoolName: school.trim(), teacherName: teacher.trim() } });
            return React.createElement('div', null,
                React.createElement('div', { className: 'card' },
                    React.createElement('h3', { className: 'mb-8' }, '🏫 اطلاعات مدرسه و معلم'),
                    React.createElement('div', { className: 'text-small text-muted mb-8' }, 'این اطلاعات بالای تصویرهای لیست (PNG) چاپ می‌شود. نام کلاس از کلاس انتخاب‌شده گرفته می‌شود.'),
                    React.createElement('input', { type: 'text', value: school, placeholder: 'نام مدرسه', onChange: e => setSchool(e.target.value), onBlur: saveInfo, style: { width: '100%', boxSizing: 'border-box', marginBottom: 8 } }),
                    React.createElement('input', { type: 'text', value: teacher, placeholder: 'نام آموزگار', onChange: e => setTeacher(e.target.value), onBlur: saveInfo, style: { width: '100%', boxSizing: 'border-box' } }))
            );
        }

        function TeacherApp"""
s, n = about.subn(about_new, s, count=1)
assert n == 1, "AboutMe component not found"

if 'native-files.bundle.js' not in s:
    s = s.replace('</body>', '<script src="./native-files.bundle.js"></script>\n</body>', 1)

p.write_text(s, encoding="utf-8")
print("App patch applied")
