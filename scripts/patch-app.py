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



# ------------------------------------------------------------
# Requested UX updates: grade inheritance, student notes, cropper,
# global day/night theme, RTL student tags and attendance cleanup.
# ------------------------------------------------------------
student_marker = "        function Students({ data, save, showToast }) {"
st = s.index(student_marker)
en = s.index("\n\n        function ", st + len(student_marker))
student = s[st:en]

student = student.replace(
"""            const [photo, setPhoto] = React.useState('');

            const students = data.students || [];
""",
"""            const [photo, setPhoto] = React.useState('');
            const [studentNote, setStudentNote] = React.useState('');
            const [cropSrc, setCropSrc] = React.useState('');
            const [cropOpen, setCropOpen] = React.useState(false);
            const [cropZoom, setCropZoom] = React.useState(1);
            const [cropX, setCropX] = React.useState(50);
            const [cropY, setCropY] = React.useState(50);

            const students = data.students || [];
            React.useEffect(() => {
                if (!editingId && students.length) {
                    const inherited = students[0].grade || guessGradeFromText(students[0].className);
                    if (inherited) setGrade(inherited);
                }
            }, [students.length, editingId]);
            const beginCrop = file => {
                const reader = new FileReader();
                reader.onload = () => {
                    setCropSrc(String(reader.result || ''));
                    setCropZoom(1); setCropX(50); setCropY(50);
                    setCropOpen(true);
                };
                reader.onerror = () => showToast('خواندن عکس ممکن نشد', 'error');
                reader.readAsDataURL(file);
            };
            const applyCrop = () => {
                const image = new Image();
                image.onload = () => {
                    const side = Math.min(image.naturalWidth, image.naturalHeight) / cropZoom;
                    const sx = (image.naturalWidth - side) * cropX / 100;
                    const sy = (image.naturalHeight - side) * cropY / 100;
                    const canvas = document.createElement('canvas');
                    canvas.width = 600; canvas.height = 600;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(image, sx, sy, side, side, 0, 0, 600, 600);
                    setPhoto(canvas.toDataURL('image/jpeg', 0.78));
                    setCropOpen(false); setCropSrc('');
                };
                image.onerror = () => showToast('برش عکس انجام نشد', 'error');
                image.src = cropSrc;
            };
""",1)

student = student.replace(
"""                                photo: photo || s.photo || ''
""",
"""                                photo: photo || s.photo || '',
                                note: studentNote.trim()
""",1)
student = student.replace(
"""                        photo
                    };
""",
"""                        photo,
                        note: studentNote.trim()
                    };
""",1)
student = student.replace(
"""                setGrade('');
                setPhoto('');
                setEditingId(null);
""",
"""                setGrade(students.length ? (students[0].grade || guessGradeFromText(students[0].className)) : '');
                setPhoto('');
                setStudentNote('');
                setEditingId(null);
""",1)
student = student.replace(
"""                setPhoto(s.photo || '');
                setEditingId(s.id);
""",
"""                setPhoto(s.photo || '');
                setStudentNote(s.note || '');
                setEditingId(s.id);
""",1)
student = student.replace(
"""                setGrade('');
                setEditingId(null);
            };
""",
"""                setGrade(students.length ? (students[0].grade || guessGradeFromText(students[0].className)) : '');
                setStudentNote('');
                setEditingId(null);
            };
""",1)

# New students inherit the first student's grade; only the first student selects it.
student = student.replace(
"""                if (!grade) {
                    showToast('پایه‌ی دانش‌آموز را انتخاب کنید', 'error');
                    return;
                }
""",
"""                const effectiveGrade = editingId ? grade : (students.length ? (students[0].grade || guessGradeFromText(students[0].className) || grade) : grade);
                if (!effectiveGrade) {
                    showToast('برای ثبت اولین دانش‌آموز، ابتدا پایه را انتخاب کنید', 'error');
                    return;
                }
""",1)
student = student.replace("                                grade,\n                                className: GRADE_LABELS[grade] || '',",
                        "                                grade: effectiveGrade,\n                                className: GRADE_LABELS[effectiveGrade] || '',",1)
student = student.replace("                        grade,\n                        className: GRADE_LABELS[grade] || '',",
                        "                        grade: effectiveGrade,\n                        className: GRADE_LABELS[effectiveGrade] || '',",1)

# Replace photo picker with an editable crop workflow.
old_photo = """                        photo ? React.createElement('img', { src: photo, alt: 'عکس دانش‌آموز', style: { width: 58, height: 58, borderRadius: '50%', objectFit: 'cover', border: '2px solid #1F8A94' } }) : null,
                        React.createElement('label', { style: { flex: 1, display: 'block', padding: 10, border: '1px dashed #1F8A94', borderRadius: 10, cursor: 'pointer', textAlign: 'center' } },
                            '📷 انتخاب عکس دانش‌آموز',
                            React.createElement('input', { type: 'file', accept: 'image/*', style: { display: 'block', width: '100%', marginTop: 6 }, onChange: async e => { const f=e.target.files && e.target.files[0]; if(!f) return; try { setPhoto(await compressImage(f, 500, 0.65)); } catch(err) { showToast('خواندن عکس ممکن نشد','error'); } } })
                        )
"""
new_photo = """                        photo ? React.createElement('img', { src: photo, alt: 'عکس دانش‌آموز', style: { width: 58, height: 58, borderRadius: '50%', objectFit: 'cover', border: '2px solid #1F8A94' } }) : null,
                        React.createElement('label', { style: { flex: 1, display: 'block', padding: 10, border: '1px dashed #1F8A94', borderRadius: 10, cursor: 'pointer', textAlign: 'center' } },
                            photo ? '📷 تغییر عکس / برش دوباره' : '📷 انتخاب عکس دانش‌آموز',
                            React.createElement('input', { type: 'file', accept: 'image/*', style: { display: 'block', width: '100%', marginTop: 6 }, onChange: e => { const f=e.target.files && e.target.files[0]; if(f) beginCrop(f); e.target.value=''; } })
                        )
"""
assert old_photo in student, "Student photo picker not found"
student = student.replace(old_photo,new_photo,1)

# Add private/important student note field.
photo_anchor = "                    React.createElement('div', { className: 'mb-8', style: { display: 'flex', alignItems: 'center', gap: 10 } },"
student = student.replace(photo_anchor,
"""                    React.createElement('div', { className: 'mb-8' },
                        React.createElement('label', { style: { display: 'block', fontWeight: 700, marginBottom: 6 } }, '📝 نکته (بیماری، مشکل خاص، شرایط خانوادگی و...)'),
                        React.createElement('textarea', { rows: 3, value: studentNote, onChange: e => setStudentNote(e.target.value), placeholder: 'مثلاً حساسیت دارویی، بیماری، نیاز آموزشی ویژه یا شرایط خانوادگی...', style: { width: '100%', boxSizing: 'border-box', padding: 10, borderRadius: 8, resize: 'vertical' } })
                    ),
""" + photo_anchor,1)

# Grade selector only for first student in a class (or when editing).
grade_block = """                    React.createElement('div', { className: 'mb-8' },
                        React.createElement('select', {
                            value: grade,
                            onChange: e => setGrade(e.target.value)
                        },
                            React.createElement('option', { value: '' }, 'پایه را انتخاب کنید...'),
                            GRADE_ORDER.map(g => React.createElement('option', { key: g, value: g }, gradeName(g)))
                        )
                    ),
"""
new_grade_block = """                    (editingId || students.length === 0)
                        ? React.createElement('div', { className: 'mb-8' },
                            React.createElement('select', { value: grade, onChange: e => setGrade(e.target.value) },
                                React.createElement('option', { value: '' }, 'پایه را انتخاب کنید...'),
                                GRADE_ORDER.map(g => React.createElement('option', { key: g, value: g }, gradeName(g)))
                            )
                        )
                        : React.createElement('div', { className: 'mb-8', style: { padding: 10, borderRadius: 8, background: '#E8F5F1', color: '#176B58' } },
                            '🎓 پایه‌ی این دانش‌آموز به‌صورت خودکار از اولین دانش‌آموز کلاس تنظیم می‌شود: ',
                            gradeName(students[0].grade || guessGradeFromText(students[0].className) || grade)
                        ),
"""
assert grade_block in student, "Grade selector not found"
student = student.replace(grade_block,new_grade_block,1)

# Add crop dialog before the component's root close.
student = student.replace(
"""                )
            );
        }""",
"""                ),
                cropOpen && React.createElement('div', { style: { position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(0,0,0,.78)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 } },
                    React.createElement('div', { dir: 'rtl', style: { width: '100%', maxWidth: 390, background: '#fff', color: '#222', borderRadius: 16, padding: 16, maxHeight: '90vh', overflowY: 'auto' } },
                        React.createElement('h3', { style: { margin: '0 0 12px' } }, '✂️ برش عکس دانش‌آموز'),
                        React.createElement('div', { style: { width: 260, height: 260, maxWidth: '100%', margin: '0 auto 14px', overflow: 'hidden', borderRadius: 12, background: '#111', border: '2px solid #1F8A94' } },
                            React.createElement('img', { src: cropSrc, alt: 'پیش‌نمایش برش', style: { width: '100%', height: '100%', objectFit: 'cover', objectPosition: cropX + '% ' + cropY + '%', transform: 'scale(' + cropZoom + ')' } })
                        ),
                        React.createElement('label', { style: { display: 'block', marginBottom: 10 } }, 'بزرگ‌نمایی',
                            React.createElement('input', { type: 'range', min: 1, max: 3, step: .05, value: cropZoom, onChange: e => setCropZoom(+e.target.value), style: { width: '100%' } })
                        ),
                        React.createElement('label', { style: { display: 'block', marginBottom: 10 } }, 'جابجایی افقی',
                            React.createElement('input', { type: 'range', min: 0, max: 100, value: cropX, onChange: e => setCropX(+e.target.value), style: { width: '100%' } })
                        ),
                        React.createElement('label', { style: { display: 'block', marginBottom: 10 } }, 'جابجایی عمودی',
                            React.createElement('input', { type: 'range', min: 0, max: 100, value: cropY, onChange: e => setCropY(+e.target.value), style: { width: '100%' } })
                        ),
                        React.createElement('div', { className: 'flex gap-8' },
                            React.createElement('button', { className: 'btn-primary', onClick: applyCrop, style: { flex: 1 } }, '✔ تأیید برش'),
                            React.createElement('button', { className: 'btn-ghost', onClick: () => { setCropOpen(false); setCropSrc(''); }, style: { flex: 1 } }, 'انصراف')
                        )
                    )
                )
            );
        }""",1)

s = s[:st] + student + s[en:]

# RTL tag picker and per-student tag frequency counter.
tag_marker = "        function TeacherNotes({ data, save, showToast }) {"
ts = s.index(tag_marker)
te = s.index("\n\n        // ============================================================\n        // برنامه هفتگی کلاس", ts)
notes = s[ts:te]
notes = notes.replace(
"""            const selectedStudents = (form.studentIds || []).map(id => students.find(st => st.id === id)).filter(Boolean);
""",
"""            const selectedStudents = (form.studentIds || []).map(id => students.find(st => st.id === id)).filter(Boolean);
            const tagCounts = {};
            notes.forEach(note => (Array.isArray(note.studentIds) ? note.studentIds : []).forEach(id => { tagCounts[id] = (tagCounts[id] || 0) + 1; }));
""",1)
notes = notes.replace(
"""                        React.createElement('div', { style: { maxHeight: 180, overflowY: 'auto', border: '1px solid #E5E7EB', borderRadius: 8, padding: 8 } },
""",
"""                        React.createElement('div', { dir: 'rtl', style: { direction: 'rtl', textAlign: 'right', maxHeight: 180, overflowY: 'auto', border: '1px solid #E5E7EB', borderRadius: 8, padding: 8 } },
""",1)
notes = notes.replace(
"""                                    React.createElement('span', null, studentName(st))
""",
"""                                    React.createElement('span', { style: { flex: 1, textAlign: 'right' } }, studentName(st)),
                                    React.createElement('small', { style: { color: '#64748b', whiteSpace: 'nowrap' } }, (tagCounts[st.id] || 0) + ' بار تگ شده')
""",1)
notes = notes.replace(
"""                                React.createElement('div', { className: 'flex flex-wrap gap-4', style: { marginTop: 10 } },
""",
"""                                React.createElement('div', { dir: 'rtl', className: 'flex flex-wrap gap-4', style: { direction: 'rtl', justifyContent: 'flex-start', marginTop: 10 } },
""",1)
notes = notes.replace(
"""                                    }, '👤 ', studentName(st)))
""",
"""                                    }, '👤 ', studentName(st), ' · ', (tagCounts[st.id] || 0), ' بار تگ‌شده'))
""",1)
s = s[:ts] + notes + s[te:]

# Remove the old attendance-only night mode control.
attendance_dark = """                    React.createElement('button', { className: cfg.darkMode ? 'btn-primary' : 'btn-ghost', onClick: () => save({ ...data, attendanceSettings: { ...cfg, darkMode: !cfg.darkMode } }) }, cfg.darkMode ? '☀️ حالت روز' : '🌙 حالت شب')),
"""
assert attendance_dark in s, "Attendance dark-mode button not found"
s = s.replace(attendance_dark, "", 1)
# The calendar control row must still close after removing its second button.
calendar_only = "                    React.createElement('button', { className: calendarOpen ? 'btn-primary' : 'btn-ghost', onClick: () => setCalendarOpen(v => !v) }, calendarOpen ? 'بستن تقویم ماهانه' : '📅 تقویم شمسی ماهانه'),\n                calendarOpen &&"
calendar_closed = "                    React.createElement('button', { className: calendarOpen ? 'btn-primary' : 'btn-ghost', onClick: () => setCalendarOpen(v => !v) }, calendarOpen ? 'بستن تقویم ماهانه' : '📅 تقویم شمسی ماهانه')),\n                calendarOpen &&"
assert calendar_only in s, "Calendar control row marker not found"
s = s.replace(calendar_only, calendar_closed, 1)

# Add app-wide persistent theme state in the main application component.
teacher_start = s.index("        function TeacherApp({ data: rootData")
teacher_end = s.index("\n\n        // ============================================================", teacher_start)
teacher = s[teacher_start:teacher_end]
teacher = teacher.replace(
"""            const rootClasses = Array.isArray(rootData.classes) ? rootData.classes : [];
""",
"""            const rootClasses = Array.isArray(rootData.classes) ? rootData.classes : [];
            const [darkMode, setDarkMode] = React.useState(() => {
                try { return localStorage.getItem('teacherAppTheme') === 'dark'; } catch (_) { return false; }
            });
            React.useEffect(() => {
                document.body.classList.toggle('app-dark', darkMode);
                document.documentElement.style.colorScheme = darkMode ? 'dark' : 'light';
                try { localStorage.setItem('teacherAppTheme', darkMode ? 'dark' : 'light'); } catch (_) {}
                return () => { document.body.classList.remove('app-dark'); document.documentElement.style.colorScheme = ''; };
            }, [darkMode]);
""",1)
teacher = teacher.replace(
"""                    onWeekly: () => setWeeklyOpen(true)
""",
"""                    onWeekly: () => setWeeklyOpen(true),
                    darkMode,
                    onToggleDark: () => setDarkMode(v => !v)
""",1)
teacher = teacher.replace(
"""            return React.createElement('div', { className: 'container' },
""",
"""            return React.createElement('div', { className: 'container app-shell' },
""",1)
s = s[:teacher_start] + teacher + s[teacher_end:]

# Put global theme switch immediately to the left of the creator button.
s = s.replace(
"""        function AppHeader({ title, user, onLogout, onWeekly }) {""",
"""        function AppHeader({ title, user, onLogout, onWeekly, darkMode, onToggleDark }) {""",1)
creator_button = """                    onLogout && React.createElement('button', { onClick: () => window.alert('ساخته شده با ❤ توسط متین دشتبان برای معلمان دلسوز ایران زمین\\n\\ntelegram: @matindashtban'), className: 'btn-ghost text-small', style: { padding: '6px 10px', borderRadius: 10, fontSize: 12, cursor: 'pointer' } }, 'درباره سازنده')"""
assert creator_button in s, "Creator button not found"
s = s.replace(creator_button,
"""                    React.createElement('button', { onClick: onToggleDark, className: 'btn-ghost text-small', title: darkMode ? 'تغییر به حالت روز' : 'تغییر به حالت شب', 'aria-label': 'تغییر حالت نمایش', style: { padding: '6px 10px', borderRadius: 10, fontSize: 12, cursor: 'pointer' } }, darkMode ? '☀️ حالت روز' : '🌙 حالت شب'),
""" + creator_button,1)


# Keep the active class's student form state isolated when switching classes.
s = s.replace(
    "tab === 'students' && React.createElement(Students, { data, save, showToast })",
    "tab === 'students' && React.createElement(Students, { key: activeClass.id, data, save, showToast })",
    1
)

# Show the saved student note in the expanded student profile.
student_note_detail = """React.createElement('li', null, \`شماره تماس مادر: \${s.motherPhone || '—'}\`)"""
assert student_note_detail in s, "Student detail list insertion point not found"
s = s.replace(
    student_note_detail,
    student_note_detail + """,
                                React.createElement('li', { style: { color: s.note ? '#9A3412' : '#64748b', fontWeight: s.note ? 700 : 400, whiteSpace: 'pre-wrap' } }, \`📝 نکته: \${s.note || 'ثبت نشده'}\`)""",
    1
)

# Keep the selected tag chips RTL as well.
s = s.replace(
    "selectedStudents.length > 0 && React.createElement('div', { className: 'flex flex-wrap gap-4', style: { marginBottom: 8 } },",
    "selectedStudents.length > 0 && React.createElement('div', { dir: 'rtl', className: 'flex flex-wrap gap-4', style: { direction: 'rtl', justifyContent: 'flex-start', marginBottom: 8 } },",
    1
)

# Broad, app-wide dark palette (all tabs, cards, controls, dialogs and menus).
dark_css = r"""
<style id="global-theme-styles">
body.app-dark{background:#0b1220!important;color:#e5e7eb!important;color-scheme:dark}
body.app-dark .container{color:#e5e7eb}
body.app-dark .header,body.app-dark .card,body.app-dark .class-manager-card,
body.app-dark .tab-bar,body.app-dark .record-row,body.app-dark .modal-content,
body.app-dark .attendance-calendar,body.app-dark .attendance-calendar-day{
 background:#172235!important;color:#e5e7eb!important;border-color:#334155!important
}
body.app-dark .tab-bar button{color:#cbd5e1!important}
body.app-dark .tab-bar button.active{background:#0f766e!important;color:#fff!important}
body.app-dark input,body.app-dark textarea,body.app-dark select,
body.app-dark button.btn-ghost,body.app-dark .attendance-calendar-day{
 background:#0f172a!important;color:#e5e7eb!important;border-color:#475569!important
}
body.app-dark input::placeholder,body.app-dark textarea::placeholder{color:#94a3b8!important}
body.app-dark .text-muted,body.app-dark .text-small{color:#a8b6c9}
body.app-dark .empty-state,body.app-dark .badge{color:#e2e8f0}
body.app-dark .attendance-calendar-day.selected{background:#134e4a!important;border-color:#2dd4bf!important}
body.app-dark .attendance-calendar-day.holiday{background:#4c1d2a!important;color:#fecdd3!important}
body.app-dark .record-row,body.app-dark .student-card,body.app-dark .list-item{background:#172235!important;color:#e5e7eb!important}
body.app-dark table,body.app-dark th,body.app-dark td{border-color:#334155!important;color:#e5e7eb!important}
body.app-dark .card[style*="background: #FCFBF7"],body.app-dark .card[style*="background:#FCFBF7"]{background:#172235!important}
body.app-dark .modal,body.app-dark [role="dialog"]{color:#e5e7eb}
body.app-dark .header-logo{filter:brightness(.9)}
body.app-dark hr{border-color:#334155}
</style>
"""
if 'id="global-theme-styles"' not in s:
    s = s.replace("</head>", dark_css + "\n</head>", 1)


rating = re.compile(r"\s*React\.createElement\('button', \{\s*onClick: function\(\) \{.*?\}, '⭐ ثبت نظر'\),", re.S)
s, removed = rating.subn("\n", s, count=1)
assert removed == 1, "Rating button not found"

if 'native-files.bundle.js' not in s:
    s = s.rsplit('</body>', 1)[0] + '<script src="./native-files.bundle.js"></script>\n</body>' + s.rsplit('</body>', 1)[1]

p.write_text(s, encoding="utf-8")
print("App patch applied")
