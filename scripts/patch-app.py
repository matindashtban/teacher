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
                    const filename = 'backup-daftar-kelas-' + todayISO() + '.json';
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

notes_start = s.index("        function TeacherNotes({ data, save, showToast }) {")
notes_end = s.index("\n\n        // ============================================================\n        // برنامه هفتگی کلاس", notes_start)
notes_component = r'''        function TeacherNotes({ data, save, showToast }) {
            const notes = Array.isArray(data.teacherNotes) ? data.teacherNotes : [];
            const students = Array.isArray(data.students) ? data.students : [];
            const studentName = st => st.name || [st.firstName, st.lastName].filter(Boolean).join(' ') || 'دانش‌آموز';
            const blank = { date: todayISO(), text: '', studentIds: [] };
            const [form, setForm] = React.useState(blank);
            const [editingId, setEditingId] = React.useState(null);
            const [search, setSearch] = React.useState('');
            const [studentSearch, setStudentSearch] = React.useState('');
            const setField = (key, value) => setForm(prev => ({ ...prev, [key]: value }));
            const reset = () => {
                setForm({ ...blank, date: todayISO() });
                setEditingId(null);
                setStudentSearch('');
            };
            const toggleStudent = id => setForm(prev => ({
                ...prev,
                studentIds: prev.studentIds.includes(id)
                    ? prev.studentIds.filter(x => x !== id)
                    : [...prev.studentIds, id]
            }));
            const saveNote = () => {
                if (!form.date) return showToast('تاریخ یادداشت را وارد کنید', 'error');
                if (!form.text.trim()) return showToast('متن یادداشت را وارد کنید', 'error');
                const note = {
                    id: editingId || uid(),
                    date: form.date,
                    text: form.text.trim(),
                    studentIds: Array.isArray(form.studentIds) ? form.studentIds : []
                };
                const next = editingId
                    ? notes.map(n => n.id === editingId ? note : n)
                    : [...notes, note];
                const ok = save({ ...data, teacherNotes: next });
                if (ok !== false) {
                    showToast(editingId ? '✏️ یادداشت ویرایش شد' : '✅ یادداشت ثبت شد');
                    reset();
                }
            };
            const edit = note => {
                setEditingId(note.id);
                setForm({ date: note.date || todayISO(), text: note.text || '', studentIds: Array.isArray(note.studentIds) ? note.studentIds : [] });
                window.scrollTo({ top: 0, behavior: 'smooth' });
            };
            const remove = id => {
                if (!confirm('این یادداشت حذف شود؟')) return;
                const ok = save({ ...data, teacherNotes: notes.filter(n => n.id !== id) });
                if (ok !== false) {
                    if (editingId === id) reset();
                    showToast('🗑️ یادداشت حذف شد');
                }
            };
            const norm = value => String(value || '').toLowerCase().replace(/ي/g, 'ی').replace(/ك/g, 'ک').replace(/\s+/g, ' ').trim();
            const sorted = [...notes].sort((a, b) => (b.date || '').localeCompare(a.date || ''));
            const filtered = sorted.filter(note => {
                if (!norm(search)) return true;
                const tagged = (Array.isArray(note.studentIds) ? note.studentIds : [])
                    .map(id => students.find(st => st.id === id))
                    .filter(Boolean).map(studentName).join(' ');
                return norm([note.text, note.date, getShamsiWithDay(note.date), tagged].join(' ')).includes(norm(search));
            });
            const inputStyle = {
                width: '100%', boxSizing: 'border-box', padding: '10px 12px',
                border: '1px solid #D8D3C7', borderRadius: 8, background: '#fff',
                fontFamily: "'Vazirmatn', Tahoma, sans-serif"
            };
            const labelStyle = { display: 'block', fontWeight: 700, marginBottom: 6, fontSize: 13 };
            const visibleStudents = [...students].sort((a,b) => studentName(a).localeCompare(studentName(b), 'fa'))
                .filter(st => norm(studentName(st)).includes(norm(studentSearch)));
            const selectedStudents = (form.studentIds || []).map(id => students.find(st => st.id === id)).filter(Boolean);
            return React.createElement('div', null,
                React.createElement('div', { className: 'card' },
                    React.createElement('h4', { className: 'mb-8' }, editingId ? '✏️ ویرایش یادداشت' : '🗒️ یادداشت جدید'),
                    React.createElement('div', { className: 'mb-8' },
                        React.createElement('label', { style: labelStyle }, 'تاریخ'),
                        React.createElement(JalaliDatePicker, { value: form.date, onChange: v => setField('date', v) })
                    ),
                    React.createElement('div', { className: 'mb-8' },
                        React.createElement('label', { style: labelStyle }, 'متن یادداشت'),
                        React.createElement('textarea', {
                            rows: 7, value: form.text,
                            onChange: e => setField('text', e.target.value),
                            placeholder: 'یادداشت خود را برای این تاریخ بنویسید...',
                            style: { ...inputStyle, resize: 'vertical', lineHeight: 1.9 }
                        })
                    ),
                    React.createElement('div', { className: 'mb-8' },
                        React.createElement('label', { style: labelStyle }, '🏷️ تگ دانش‌آموزان (اختیاری)'),
                        React.createElement('input', {
                            value: studentSearch, onChange: e => setStudentSearch(e.target.value),
                            placeholder: 'جستجوی نام دانش‌آموز...',
                            style: { ...inputStyle, marginBottom: 8 }
                        }),
                        selectedStudents.length > 0 && React.createElement('div', { className: 'flex flex-wrap gap-4', style: { marginBottom: 8 } },
                            selectedStudents.map(st => React.createElement('span', {
                                key: st.id, style: { background: '#E8F3FF', color: '#245B91', borderRadius: 20, padding: '4px 9px', fontSize: 12 }
                            }, studentName(st), ' ', React.createElement('button', {
                                type: 'button', onClick: () => toggleStudent(st.id), style: { border: 0, background: 'transparent', color: 'inherit', fontWeight: 700 }
                            }, '×')))
                        ),
                        React.createElement('div', { style: { maxHeight: 180, overflowY: 'auto', border: '1px solid #E5E7EB', borderRadius: 8, padding: 8 } },
                            visibleStudents.length
                                ? visibleStudents.map(st => React.createElement('label', {
                                    key: st.id, style: { display: 'flex', alignItems: 'center', gap: 8, padding: '6px 2px', cursor: 'pointer' }
                                },
                                    React.createElement('input', { type: 'checkbox', checked: (form.studentIds || []).includes(st.id), onChange: () => toggleStudent(st.id) }),
                                    React.createElement('span', null, studentName(st))
                                ))
                                : React.createElement('div', { className: 'text-muted text-small' }, students.length ? 'دانش‌آموزی با این نام پیدا نشد.' : 'ابتدا دانش‌آموزان را در برنامه ثبت کنید.')
                        )
                    ),
                    React.createElement('div', { className: 'flex flex-wrap gap-4' },
                        React.createElement('button', { onClick: saveNote, className: 'btn-primary' }, editingId ? '💾 ذخیره تغییرات' : '➕ ثبت یادداشت'),
                        editingId && React.createElement('button', { onClick: reset, className: 'btn-secondary' }, 'انصراف')
                    )
                ),
                React.createElement('div', { className: 'card' },
                    React.createElement('h4', { className: 'mb-8' }, '📚 دفترچه یادداشت‌ها (' + filtered.length + ' از ' + notes.length + ')'),
                    React.createElement('input', {
                        value: search, onChange: e => setSearch(e.target.value),
                        placeholder: '🔎 جستجو در متن، تاریخ یا نام دانش‌آموز تگ‌شده...',
                        style: inputStyle
                    }),
                    filtered.length === 0
                        ? React.createElement('div', { className: 'empty-state' }, React.createElement('p', null, notes.length ? 'یادداشتی مطابق جستجوی شما پیدا نشد.' : 'هنوز یادداشتی ثبت نشده است.'))
                        : filtered.map(note => {
                            const tagged = (Array.isArray(note.studentIds) ? note.studentIds : [])
                                .map(id => students.find(st => st.id === id)).filter(Boolean);
                            return React.createElement('div', {
                                key: note.id,
                                style: { border: '1px solid #E9DFF0', borderRadius: 12, padding: 16, marginBottom: 12, background: '#FCFBF7' }
                            },
                                React.createElement('div', { className: 'text-muted text-small', style: { marginBottom: 10 } }, '📅 ' + getShamsiWithDay(note.date)),
                                React.createElement('div', { style: { whiteSpace: 'pre-wrap', lineHeight: 1.9 } }, note.text),
                                tagged.length > 0 && React.createElement('div', { className: 'flex flex-wrap gap-4', style: { marginTop: 10 } },
                                    tagged.map(st => React.createElement('span', {
                                        key: st.id, style: { background: '#E8F3FF', color: '#245B91', borderRadius: 20, padding: '4px 9px', fontSize: 12 }
                                    }, '👤 ', studentName(st)))
                                ),
                                React.createElement('div', { className: 'flex gap-4', style: { marginTop: 12 } },
                                    React.createElement('button', { onClick: () => edit(note), className: 'btn-secondary' }, '✏️ ویرایش'),
                                    React.createElement('button', { onClick: () => remove(note.id), className: 'btn-danger' }, '🗑️ حذف')
                                )
                            );
                        })
                )
            );
        }'''
s = s[:notes_start] + notes_component + s[notes_end:]

rating = re.compile(r"\s*React\.createElement\('button', \{\s*onClick: function\(\) \{.*?\}, '⭐ ثبت نظر'\),", re.S)
s, removed = rating.subn("\n", s, count=1)
assert removed == 1, "Rating button not found"

if 'native-files.bundle.js' not in s:
    s = s.rsplit('</body>', 1)[0] + '<script src="./native-files.bundle.js"></script>\n</body>' + s.rsplit('</body>', 1)[1]

p.write_text(s, encoding="utf-8")
print("App patch applied")
