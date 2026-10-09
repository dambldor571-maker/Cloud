# Інтерактивний 3D-перегляд

`zmiy_viewer.html` — сторінка на three.js (r160): обертання/масштаб/зсув, ракурси, вмикання складових
(з кількістю трикутників), розібраний вигляд, каркас. Публікується як артефакт claude.ai разом із моделлю.

Сервіс сторінок не віддає `.glb`, тому модель кладеться поруч як base64-текст:

```
python3 -c "import base64;open('zmiy_logistic_glb.txt','w').write(base64.b64encode(open('../zmiy_logistic.glb','rb').read()).decode())"
```

і публікується файлами `zmiy_viewer.html` + `zmiy_logistic_glb.txt` (у git `.txt` не зберігається — це копія GLB).
Опублікована сторінка (приватна, доступ власника): https://claude.ai/artifact/Mn1sSAoy27o12A26bUQdbL
