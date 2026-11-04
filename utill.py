"""Run: python utill.py. Optional JPEG support: pip install Pillow."""
import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'graph.json'


def new_graph():
    return {'version': 1, 'coordinate_system': 'image_pixels_top_left',
            'weight_unit': 'seconds', 'image': None, 'nodes': [], 'edges': []}


def number(value):
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError('0 이상의 유한한 숫자를 입력하세요.')
    return result


class Editor:
    def __init__(self, root):
        self.root = root
        self.graph = new_graph()
        self.selected = None
        self.start = None
        self.image = None
        self.dirty = False
        self.mode = tk.StringVar(value='select')
        root.title('PBL 1 · 지도 그래프 편집기')
        root.geometry('1250x900')
        root.configure(bg='#000000')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', background='#000000', foreground='#eeeeee')
        style.configure('TEntry', fieldbackground='#202020', foreground='#ffffff')
        style.configure('TButton', background='#252525', foreground='#ffffff')
        style.map('TButton', background=[('active', '#444444')])
        style.map('TRadiobutton', background=[('active', '#252525')])
        bar = ttk.Frame(root, padding=8)
        bar.pack(fill='x')
        for label, command in [('저장', self.save)]:
            ttk.Button(bar, text=label, command=command).pack(side='left', padx=3)
        for label, mode in [('선택 / 위치 이동', 'select'), ('노드 추가', 'add'), ('구간 연결', 'edge')]:
            ttk.Radiobutton(bar, text=label, variable=self.mode, value=mode,
                            command=self.reset_start).pack(side='left', padx=8)
        ttk.Label(bar, text='Ctrl+S 저장 · Delete 선택 항목 삭제').pack(side='right')
        body = ttk.Frame(root)
        body.pack(fill='both', expand=True)
        left = ttk.Frame(body)
        left.pack(side='left', fill='both', expand=True)
        self.canvas = tk.Canvas(left, bg='#000000', highlightthickness=0)
        xbar = ttk.Scrollbar(left, orient='horizontal', command=self.canvas.xview)
        ybar = ttk.Scrollbar(left, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        ybar.grid(row=0, column=1, sticky='ns')
        xbar.grid(row=1, column=0, sticky='ew')
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        side = ttk.Frame(body, padding=12, width=290)
        side.pack(side='right', fill='y')
        ttk.Label(side, text='선택 항목', font=('', 13, 'bold')).pack(anchor='w')
        self.fields = {}
        for key, title in [('name', '노드 이름'), ('x', 'X 위치 (px)'), ('y', 'Y 위치 (px)'), ('elevation_m', '높이 / 고도 (m)'),
                           ('weight', '기본 통과 시간 (초)'), ('peak_delay', '혼잡 추가 지연 (초)')]:
            ttk.Label(side, text=title).pack(anchor='w', pady=(10, 2))
            field = ttk.Entry(side, width=28)
            field.pack(fill='x')
            self.fields[key] = field
        ttk.Button(side, text='변경 적용', command=self.apply).pack(fill='x', pady=(12, 4))
        ttk.Button(side, text='선택 항목 삭제', command=self.delete).pack(fill='x')
        ttk.Label(side, text='노드 / 구간 목록').pack(anchor='w', pady=(18, 4))
        self.items = tk.Listbox(side, height=12, exportselection=False, bg='#151515', fg='#eeeeee', selectbackground='#375b85')
        self.items.pack(fill='both', expand=True)
        self.items.bind('<<ListboxSelect>>', self.list_select)
        ttk.Label(side, text='연결은 방향이 있습니다.\n왕복은 반대 방향도 추가하세요.\n혼잡 시간 비용 = 기본 시간 + 지연', wraplength=260).pack(anchor='w', pady=12)
        self.status = tk.StringVar(value='assets/map.png 자동 로드 · 노드를 클릭해 편집하세요.')
        ttk.Label(root, textvariable=self.status, padding=8).pack(fill='x')
        self.pointer = tk.StringVar(value='마우스 지도 좌표: — (이미지 픽셀)')
        ttk.Label(root, textvariable=self.pointer, padding=8).pack(fill='x')
        self.canvas.bind('<Motion>', self.track_mouse)
        self.canvas.bind('<Leave>', lambda event: self.pointer.set('마우스 지도 좌표: —'))
        self.canvas.bind('<Button-1>', self.click)
        self.canvas.bind('<B1-Motion>', self.drag)
        root.bind('<Control-s>', lambda event: self.save())
        root.bind('<Delete>', lambda event: self.delete() if root.focus_get() == self.canvas else None)
        root.protocol('WM_DELETE_WINDOW', self.close)
        if DATA.exists():
            try:
                self.graph = json.loads(DATA.read_text(encoding='utf-8'))
            except Exception as exc:
                messagebox.showerror('데이터 읽기 실패', str(exc))
        try:
            self.load_image()
        except Exception as exc:
            messagebox.showerror('지도 읽기 실패', str(exc))
        self.draw()

    def track_mouse(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.pointer.set(f'마우스 지도 좌표: X={x:.1f}, Y={y:.1f} px | 높이는 직접 입력 (m)')

    def reset_start(self):
        self.start = None
        self.status.set('노드 추가: 빈 곳 클릭 / 구간 연결: 출발 노드, 도착 노드 순서로 클릭')
        self.draw()

    def load_image(self):
        path = ROOT / 'assets' / 'map.png'
        if not path.exists():
            raise FileNotFoundError(f'지도 파일을 넣어주세요: {path}')
        try:
            from PIL import Image, ImageTk
            with Image.open(path) as source:
                photo = ImageTk.PhotoImage(source)
        except ImportError:
            photo = tk.PhotoImage(file=str(path))
        info = self.graph.get('image')
        if info and self.graph['nodes'] and (photo.width(), photo.height()) != (info['width'], info['height']):
            raise ValueError('map.png 크기가 기존 노드의 좌표 기준과 다릅니다. 기존 크기의 지도를 사용하세요.')
        self.image = photo
        self.graph['image'] = {'path': 'assets/map.png', 'width': photo.width(), 'height': photo.height()}

    def node_at(self, x, y):
        return next((n for n in reversed(self.graph['nodes']) if math.hypot(n['x']-x, n['y']-y) <= 12), None)

    def click(self, event):
        self.canvas.focus_set()
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        node = self.node_at(x, y)
        if self.mode.get() == 'add' and not node:
            if not self.image or not (0 <= x < self.image.width() and 0 <= y < self.image.height()):
                return
            name = simpledialog.askstring('노드 추가', '지점 이름:', parent=self.root)
            if not name or not name.strip():
                return
            index = 1
            while any(n['id'] == f'n{index}' for n in self.graph['nodes']):
                index += 1
            node = {'id': f'n{index}', 'name': name.strip(), 'x': round(x, 2), 'y': round(y, 2), 'elevation_m': 0.0}
            self.graph['nodes'].append(node)
            self.dirty = True
        if node and self.mode.get() == 'edge':
            if self.start is None:
                self.start = node['id']
                self.status.set(f"출발: {node['name']} → 도착 노드를 클릭하세요.")
            elif self.start != node['id']:
                edge = next((e for e in self.graph['edges'] if e['source'] == self.start and e['target'] == node['id']), None)
                if edge is None:
                    cost = simpledialog.askfloat('구간 연결', '기본 통과 시간 (초):', minvalue=0, parent=self.root)
                    if cost is None or not math.isfinite(cost):
                        return
                    edge = {'source': self.start, 'target': node['id'], 'weight': cost, 'peak_delay': 0.0}
                    self.graph['edges'].append(edge)
                    self.dirty = True
                self.start = None
                self.select('edge', edge)
                return
            self.draw()
        elif node:
            self.select('node', node)
        else:
            hits = self.canvas.find_overlapping(x-4, y-4, x+4, y+4)
            for item in reversed(hits):
                for tag in self.canvas.gettags(item):
                    if tag.startswith('edge:'):
                        self.select('edge', self.graph['edges'][int(tag.split(':')[1])])
                        return

    def select(self, kind, obj):
        self.selected = (kind, obj)
        for key, field in self.fields.items():
            field.delete(0, 'end')
            if key in obj and obj[key] is not None:
                field.insert(0, str(obj[key]))
        self.draw()

    def drag(self, event):
        if self.mode.get() != 'select' or not self.selected or self.selected[0] != 'node':
            return
        node = self.selected[1]
        node['x'] = round(max(0, min(self.image.width()-1, self.canvas.canvasx(event.x))), 2)
        node['y'] = round(max(0, min(self.image.height()-1, self.canvas.canvasy(event.y))), 2)
        self.dirty = True
        self.select('node', node)

    def apply(self):
        if not self.selected:
            return
        kind, obj = self.selected
        try:
            if kind == 'node':
                name = self.fields['name'].get().strip()
                x, y = number(self.fields['x'].get()), number(self.fields['y'].get())
                if not name or x >= self.image.width() or y >= self.image.height():
                    raise ValueError('이름과 이미지 범위 안의 좌표를 입력하세요.')
                height_text = self.fields['elevation_m'].get().strip()
                elevation = float(height_text) if height_text else None
                if elevation is not None and not math.isfinite(elevation):
                    raise ValueError('높이는 유한한 숫자 또는 빈칸으로 입력하세요.')
                obj.update(name=name, x=x, y=y, elevation_m=elevation)
            else:
                weight = number(self.fields['weight'].get())
                delay = number(self.fields['peak_delay'].get())
                obj.update(weight=weight, peak_delay=delay)
            self.dirty = True
            self.draw()
        except ValueError as exc:
            messagebox.showerror('입력 확인', str(exc))

    def delete(self):
        if not self.selected:
            return
        kind, obj = self.selected
        if not messagebox.askyesno('삭제', '선택 항목을 삭제할까요? 노드를 지우면 연결 구간도 삭제됩니다.'):
            return
        if kind == 'node':
            self.graph['nodes'].remove(obj)
            self.graph['edges'] = [e for e in self.graph['edges'] if obj['id'] not in (e['source'], e['target'])]
        else:
            self.graph['edges'].remove(obj)
        self.selected = self.start = None
        self.dirty = True
        self.draw()

    def list_select(self, event):
        indices = self.items.curselection()
        if indices:
            self.select(*self.rows[indices[0]])

    def draw(self):
        c = self.canvas
        c.delete('all')
        if self.image:
            c.create_image(0, 0, image=self.image, anchor='nw')
            c.configure(scrollregion=(0, 0, self.image.width(), self.image.height()))
        else:
            c.create_text(300, 180, text='assets/map.png 확인 → 노드 추가 → 구간 연결 → 저장', fill='#eeeeee', font=('', 16))
        nodes = {n['id']: n for n in self.graph['nodes']}
        self.rows = []
        self.items.delete(0, 'end')
        for i, edge in enumerate(self.graph['edges']):
            a, b = nodes[edge['source']], nodes[edge['target']]
            color = '#ef7c00' if self.selected and self.selected[1] is edge else '#3465a4'
            # Offset directed edges so the reverse direction stays separately clickable.
            dx, dy = b['x']-a['x'], b['y']-a['y']
            length = max(1, math.hypot(dx, dy))
            ox, oy = -dy/length*7, dx/length*7
            coords = (a['x']+ox, a['y']+oy, b['x']+ox, b['y']+oy)
            c.create_line(*coords, fill=color, width=3, arrow='last', tags=(f'edge:{i}',))
            c.create_text((a['x']+b['x'])/2+ox*2, (a['y']+b['y'])/2+oy*2,
                          text=f"{edge['weight']:g}s (+{edge['peak_delay']:g})", fill=color,
                          tags=(f'edge:{i}',))
        for node in self.graph['nodes']:
            x, y = node['x'], node['y']
            active = (self.selected and self.selected[1] is node) or self.start == node['id']
            c.create_oval(x-7, y-7, x+7, y+7, fill='#ef7c00' if active else '#d83b45', outline='white', width=2)
            c.create_text(x+11, y-12, text=node['name'], anchor='w', fill='#ffffff', font=('', 11, 'bold'))
            self.rows.append(('node', node))
            self.items.insert('end', f"● {node['name']} [{node['id']}]")
        for edge in self.graph['edges']:
            self.rows.append(('edge', edge))
            self.items.insert('end', f"→ {nodes[edge['source']]['name']} → {nodes[edge['target']]['name']}")
        self.root.title(('• ' if self.dirty else '') + 'PBL 1 · 지도 그래프 편집기')

    def save(self):
        try:
            DATA.parent.mkdir(parents=True, exist_ok=True)
            temp = DATA.with_suffix('.tmp')
            temp.write_text(json.dumps(self.graph, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
            temp.replace(DATA)
            self.dirty = False
            self.status.set(f'저장 완료: {DATA}')
            self.draw()
            return True
        except Exception as exc:
            messagebox.showerror('저장 실패', str(exc))
            return False

    def close(self):
        if self.dirty:
            answer = messagebox.askyesnocancel('저장', '변경 내용을 저장할까요?')
            if answer is None or (answer and not self.save()):
                return
        self.root.destroy()


if __name__ == '__main__':
    Editor(tk.Tk()).root.mainloop()
