# Bring your own personality / Tự viết tính cách

The public persona files are intentionally empty. For 3.x, run `keys-keys setup`:
the wizard writes your private `data/persona.md`, leaving these tracked files untouched.
Optional `data/persona-auto.md`, `data/persona-soft.md` and `data/persona-spicy.md`
select voices through `/persona`; an empty mode falls back to the base persona.
Existing installations can keep their configured `persona_file` and private variants.

Write a voice, language, addressing style, interests and boundaries. Decide how light
teasing works and when to be gentle or serious. Do not force a catchphrase into every
reply. Relationship context should guide tone without making people earn help by
appeasing the character. Permissions and task verification live in code.

VI: Wizard tạo persona riêng trong `data/`. M viết một câu trước cũng được, sửa sau.
Muốn tsundere thì thêm nét bướng và quan điểm riêng; đừng biến mọi câu trả lời thành
một bài thi xin lỗi nhân vật. Server đang cháy thì chữa cháy trước đã. 😭

Private prompts, tokens and tests do not belong in a commit. Older deployments that
filled tracked placeholders can keep `git update-index --skip-worktree` locally;
always inspect staged changes because `.gitignore` does not protect tracked files.
