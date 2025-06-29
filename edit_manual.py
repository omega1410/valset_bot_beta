import sqlite3

conn = sqlite3.connect("data.db")
c = conn.cursor()

# 🟡 покажи список разделов
c.execute("SELECT id, title FROM sections")
for row in c.fetchall():
    print(row)

# 🟢 изменить текст раздела с id=2
# c.execute("UPDATE sections SET content = ? WHERE id = ?", ("новый текст", 2))

# 🔴 удалить раздел с id=3
# c.execute("DELETE FROM sections WHERE id = ?", (9,))

conn.commit()
conn.close()
