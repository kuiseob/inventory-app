import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.ticker as ticker
    _kf = [f.name for f in fm.fontManager.ttflist
           if any(k in f.name for k in ["Gothic","Malgun","AppleGothic","NanumGothic","나눔","고딕"])]
    if _kf:
        plt.rcParams["font.family"] = _kf[0]
    plt.rcParams["axes.unicode_minus"] = False
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mfg_inventory.json")

# ── 색상 팔레트 ──────────────────────────────────────────────
C = {
    "bg":       "#F0F2F5",
    "header":   "#1A237E",
    "dash":     "#1565C0",
    "items":    "#2E7D32",
    "prod":     "#E65100",
    "io":       "#6A1B9A",
    "hist":     "#37474F",
    "graph":    "#00695C",
    "tab_fg":   "#FFFFFF",
    "tab_sel":  "#FFFFFF",
    "low":      "#FFCDD2",
    "raw":      "#BBDEFB",
    "semi":     "#FFF9C4",
    "done":     "#C8E6C9",
    "in_bg":    "#E3F2FD",
    "out_bg":   "#FFF8E1",
    "prod_bg":  "#F1F8E9",
    "cons_bg":  "#FCE4EC",
}
TYPES      = ["원자재", "반제품", "완제품"]
TYPE_BG    = {"원자재": C["raw"], "반제품": C["semi"], "완제품": C["done"]}
TYPE_BADGE = {"원자재": ("#1565C0","#E3F2FD"),
              "반제품":  ("#F57F17","#FFF9C4"),
              "완제품":  ("#2E7D32","#E8F5E9")}
ACT_BG     = {"입고": C["in_bg"], "출고": C["out_bg"],
              "생산완료": C["prod_bg"], "원자재소비": C["cons_bg"]}

# ── DB 헬퍼 ─────────────────────────────────────────────────
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return {"items":{},"bom":{},"history":[],"_seq":1}

def save(db):
    with open(DATA_FILE,"w",encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def new_id(db):
    i = str(db.get("_seq",1)); db["_seq"]=int(i)+1; return i

def now(): return datetime.now().strftime("%Y-%m-%d %H:%M")

def add_history(db, action, iid, name, qty, note=""):
    db["history"].append({"date":now(),"action":action,
                          "item_id":iid,"item_name":name,"qty":qty,"note":note})

# ── 커스텀 위젯 헬퍼 ─────────────────────────────────────────
def make_btn(parent, text, cmd, bg, fg="white", size=11, bold=True, pad=(12,6)):
    style = "bold" if bold else ""
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                     font=("맑은 고딕", size, style) if bold else ("맑은 고딕", size),
                     relief=tk.FLAT, padx=pad[0], pady=pad[1],
                     activebackground=bg, activeforeground=fg, cursor="hand2",
                     bd=0, highlightthickness=0)

def make_label(parent, text, size=11, bold=False, fg="#212121", bg=None):
    kw = {"text":text, "font":("맑은 고딕", size, "bold" if bold else ""), "fg":fg}
    if bg: kw["bg"] = bg
    return tk.Label(parent, **kw)

def make_entry(parent, var, width=22, bg="white"):
    return tk.Entry(parent, textvariable=var, font=("맑은 고딕",11),
                    width=width, relief=tk.FLAT, bd=0, bg=bg,
                    highlightthickness=1, highlightbackground="#BDBDBD",
                    highlightcolor="#1565C0", insertbackground="#1565C0")

def section_header(parent, text, color):
    f = tk.Frame(parent, bg=color)
    f.pack(fill=tk.X, pady=(10,2))
    tk.Label(f, text=f"  {text}", font=("맑은 고딕",11,"bold"),
             bg=color, fg="white", pady=5).pack(anchor=tk.W)
    return f

# ── FormDialog ───────────────────────────────────────────────
class FormDialog(tk.Toplevel):
    def __init__(self, parent, title, fields, accent="#1565C0"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=C["bg"])
        self.grab_set(); self.resizable(False,False)
        self.result = None; self._vars = {}

        # 헤더
        hf = tk.Frame(self, bg=accent)
        hf.pack(fill=tk.X)
        tk.Label(hf, text=f"  {title}", font=("맑은 고딕",12,"bold"),
                 bg=accent, fg="white", pady=10).pack(anchor=tk.W)

        body = tk.Frame(self, bg=C["bg"], padx=20, pady=12)
        body.pack(fill=tk.BOTH)

        for i,(label,default,widget,*opts) in enumerate(fields):
            tk.Label(body, text=label, font=("맑은 고딕",11),
                     bg=C["bg"], fg="#424242", anchor=tk.W).grid(
                row=i, column=0, padx=(0,10), pady=6, sticky=tk.W)
            if widget == "entry":
                var = tk.StringVar(value=str(default))
                e = make_entry(body, var, width=26)
                e.grid(row=i, column=1, pady=6, sticky=tk.EW)
            elif widget == "combo":
                var = tk.StringVar(value=str(default))
                cb = ttk.Combobox(body, textvariable=var, values=opts[0],
                                  state="readonly", width=24, font=("맑은 고딕",11))
                cb.grid(row=i, column=1, pady=6, sticky=tk.EW)
            self._vars[label] = var
            if i == 0:
                (e if widget=="entry" else cb).focus()

        # 버튼
        bf = tk.Frame(self, bg=C["bg"], pady=10)
        bf.pack(fill=tk.X, padx=20)
        make_btn(bf,"확인",self._ok,accent,pad=(20,7)).pack(side=tk.LEFT, padx=(0,8))
        make_btn(bf,"취소",self.destroy,"#757575",pad=(20,7)).pack(side=tk.LEFT)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        self.result = {k:v.get().strip() for k,v in self._vars.items()}
        self.destroy()

    def show(self):
        self.wait_window(); return self.result


# ── 메인 앱 ──────────────────────────────────────────────────
class MfgApp:
    def __init__(self, root):
        self.root = root
        self.root.title("제조업 재고관리 시스템")
        self.root.geometry("1150x720")
        self.root.configure(bg=C["header"])
        self.db = load()
        self._mpl_canvas = None
        self._build()
        self.refresh_all()

    # ── 레이아웃 ─────────────────────────────────────────────
    def _build(self):
        # ① 최상단 앱 헤더
        header = tk.Frame(self.root, bg=C["header"], pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="  ⚙  제조업 재고관리 시스템",
                 font=("맑은 고딕",15,"bold"), bg=C["header"], fg="white").pack(side=tk.LEFT)
        self.clock_lbl = tk.Label(header, font=("맑은 고딕",10),
                                  bg=C["header"], fg="#90CAF9")
        self.clock_lbl.pack(side=tk.RIGHT, padx=16)
        self._tick()

        # ② 커스텀 탭 바
        tab_defs = [
            ("재고 현황",  C["dash"],  self._show_dash),
            ("품목 관리",  C["items"], self._show_items),
            ("생산 처리",  C["prod"],  self._show_prod),
            ("입출고",     C["io"],    self._show_io),
            ("이력 조회",  C["hist"],  self._show_hist),
            ("그래프",     C["graph"], self._show_graph),
        ]
        self.tab_bar = tk.Frame(self.root, bg=C["header"])
        self.tab_bar.pack(fill=tk.X)
        self._tab_btns = {}
        for name, color, cmd in tab_defs:
            btn = tk.Button(self.tab_bar, text=f"  {name}  ",
                            font=("맑은 고딕",11,"bold"),
                            bg=color, fg="white", relief=tk.FLAT,
                            activebackground=color, activeforeground="white",
                            bd=0, pady=8, cursor="hand2",
                            command=lambda c=cmd, n=name: self._switch_tab(n, c))
            btn.pack(side=tk.LEFT, padx=2, pady=(2,0))
            self._tab_btns[name] = (btn, color)

        # ③ 콘텐츠 영역
        self.content = tk.Frame(self.root, bg=C["bg"])
        self.content.pack(fill=tk.BOTH, expand=True)

        # ④ 각 탭 페이지 빌드
        self.pages = {}
        builders = {
            "재고 현황": self._build_dash,
            "품목 관리": self._build_items,
            "생산 처리": self._build_prod,
            "입출고":    self._build_io,
            "이력 조회": self._build_hist,
            "그래프":    self._build_graph,
        }
        for name, builder in builders.items():
            page = tk.Frame(self.content, bg=C["bg"])
            self.pages[name] = page
            builder(page)

        self._current_tab = None
        self._switch_tab("재고 현황", self._show_dash)

    def _tick(self):
        self.clock_lbl.config(text=datetime.now().strftime("📅 %Y-%m-%d  🕐 %H:%M:%S"))
        self.root.after(1000, self._tick)

    def _switch_tab(self, name, cmd):
        if self._current_tab:
            self.pages[self._current_tab].pack_forget()
            btn, color = self._tab_btns[self._current_tab]
            btn.config(bg=color, relief=tk.FLAT, pady=8)
        self.pages[name].pack(fill=tk.BOTH, expand=True)
        btn, color = self._tab_btns[name]
        btn.config(bg="white", fg=color, relief=tk.FLAT, pady=10)
        self._current_tab = name
        cmd()

    def _show_dash(self):  self.refresh_dash()
    def _show_items(self): self.refresh_items()
    def _show_prod(self):  self._refresh_bom_preview()
    def _show_io(self):    self.refresh_io_hist()
    def _show_hist(self):  self.refresh_hist()
    def _show_graph(self): self.refresh_graph()

    # ── 재고 현황 탭 ─────────────────────────────────────────
    def _build_dash(self, f):
        section_header(f, "📦  전체 재고 현황", C["dash"])

        self.dash_trees = {}
        container = tk.Frame(f, bg=C["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        icons = {"원자재":"🔩","반제품":"🔧","완제품":"📦"}
        for t in TYPES:
            fg, bg = TYPE_BADGE[t]
            lf = tk.LabelFrame(container,
                               text=f"  {icons[t]}  {t}  ",
                               font=("맑은 고딕",11,"bold"),
                               fg=fg, bg=bg, pady=4, padx=4,
                               relief=tk.GROOVE, bd=2)
            lf.pack(fill=tk.BOTH, expand=True, pady=3)
            cols = ("품목명","단위","현재수량","안전재고","단가(원)","비고")
            tree = ttk.Treeview(lf, columns=cols, show="headings", height=4)
            for col, w in zip(cols,[200,60,90,90,110,200]):
                tree.heading(col, text=col)
                tree.column(col, width=w, anchor=tk.CENTER)
            tree.column("품목명", anchor=tk.W)
            tree.tag_configure("low", background=C["low"])
            tree.tag_configure("ok",  background=bg)
            sb = ttk.Scrollbar(lf, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=sb.set)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            self.dash_trees[t] = tree

        self.dash_status = tk.StringVar()
        sf = tk.Frame(f, bg=C["dash"])
        sf.pack(fill=tk.X)
        tk.Label(sf, textvariable=self.dash_status,
                 font=("맑은 고딕",10), bg=C["dash"], fg="white",
                 anchor=tk.W, padx=12, pady=5).pack(fill=tk.X)

    def refresh_dash(self):
        for t in TYPES:
            for r in self.dash_trees[t].get_children():
                self.dash_trees[t].delete(r)
        low_list = []
        for iid, item in self.db["items"].items():
            tree = self.dash_trees[item["type"]]
            qty, minq = item["quantity"], item["min_qty"]
            tag = "low" if qty <= minq else "ok"
            tree.insert("", tk.END, values=(
                item["name"], item["unit"], qty, minq,
                f"{item['cost']:,.0f}", item.get("note","")), tags=(tag,))
            if qty <= minq:
                low_list.append(item["name"])
        n = len(self.db["items"])
        self.dash_status.set(
            f"  총 {n}개 품목  |  ⚠ 안전재고 미달: {len(low_list)}개"
            + (f"  →  {', '.join(low_list[:6])}" if low_list else "  ✅ 이상 없음"))

    # ── 품목 관리 탭 ─────────────────────────────────────────
    def _build_items(self, f):
        # 버튼 바
        bf = tk.Frame(f, bg=C["items"], pady=8)
        bf.pack(fill=tk.X)
        for label, cmd, bg in [
            ("＋  품목 추가", self.add_item,    "#43A047"),
            ("✏  수정",      self.edit_item,   "#1E88E5"),
            ("🗑  삭제",      self.delete_item, "#E53935"),
            ("⚙  BOM 설정", self.edit_bom,    "#8E24AA"),
        ]:
            make_btn(bf, label, cmd, bg).pack(side=tk.LEFT, padx=6, pady=2)

        # 검색/필터 바
        sf = tk.Frame(f, bg="#E8EAF6", pady=6)
        sf.pack(fill=tk.X, padx=0)
        tk.Label(sf, text="  분류:", font=("맑은 고딕",11), bg="#E8EAF6").pack(side=tk.LEFT)
        self.filter_type = tk.StringVar(value="전체")
        ttk.Combobox(sf, textvariable=self.filter_type,
                     values=["전체"]+TYPES, state="readonly",
                     width=10, font=("맑은 고딕",11)).pack(side=tk.LEFT, padx=6)
        self.filter_type.trace_add("write", lambda *_: self.refresh_items())

        tk.Label(sf, text="🔍 실시간 검색:", font=("맑은 고딕",11), bg="#E8EAF6").pack(side=tk.LEFT, padx=(12,4))
        self.item_search = tk.StringVar()
        self.item_search.trace_add("write", lambda *_: self.refresh_items())
        e = make_entry(sf, self.item_search, width=22)
        e.pack(side=tk.LEFT, padx=4)

        self.item_count_lbl = tk.Label(sf, font=("맑은 고딕",10),
                                       bg="#E8EAF6", fg="#5C6BC0")
        self.item_count_lbl.pack(side=tk.RIGHT, padx=12)

        # 테이블
        cols = ("ID","품목명","분류","단위","현재수량","안전재고","단가(원)","비고")
        self.item_tree = self._make_tree(f, cols, [40,200,80,60,90,90,110,180])
        for t, bg in TYPE_BG.items():
            self.item_tree.tag_configure(t,   background=bg)
        self.item_tree.tag_configure("low", background=C["low"])

    def refresh_items(self):
        t = self.item_tree
        for r in t.get_children(): t.delete(r)
        kw = self.item_search.get().lower()
        ft = self.filter_type.get()
        cnt = 0
        for iid, item in self.db["items"].items():
            if ft != "전체" and item["type"] != ft: continue
            if kw and kw not in item["name"].lower(): continue
            qty = item["quantity"]
            tags = ("low",) if qty <= item["min_qty"] else (item["type"],)
            t.insert("", tk.END, iid=iid, values=(
                iid, item["name"], item["type"], item["unit"],
                qty, item["min_qty"], f"{item['cost']:,.0f}", item.get("note","")),
                tags=tags)
            cnt += 1
        self.item_count_lbl.config(text=f"검색결과: {cnt}개")

    def add_item(self):
        r = FormDialog(self.root,"품목 추가",[
            ("품목명","","entry"),("분류","원자재","combo",TYPES),
            ("단위","개","entry"),("현재수량","0","entry"),
            ("안전재고","10","entry"),("단가(원)","0","entry"),("비고","","entry"),
        ], accent=C["items"]).show()
        if not r: return
        if not r["품목명"]:
            messagebox.showwarning("오류","품목명을 입력하세요."); return
        try:
            qty=float(r["현재수량"]); minq=float(r["안전재고"]); cost=float(r["단가(원)"])
        except ValueError:
            messagebox.showwarning("오류","수량/단가는 숫자로 입력하세요."); return
        iid = new_id(self.db)
        self.db["items"][iid] = {"name":r["품목명"],"type":r["분류"],"unit":r["단위"],
                                  "quantity":qty,"min_qty":minq,"cost":cost,
                                  "note":r["비고"],"created":now()}
        save(self.db); self.refresh_all()

    def edit_item(self):
        sel = self.item_tree.selection()
        if not sel: messagebox.showwarning("선택 필요","품목을 먼저 선택하세요."); return
        iid = sel[0]; item = self.db["items"][iid]
        r = FormDialog(self.root,"품목 수정",[
            ("품목명",item["name"],"entry"),("분류",item["type"],"combo",TYPES),
            ("단위",item["unit"],"entry"),("안전재고",item["min_qty"],"entry"),
            ("단가(원)",item["cost"],"entry"),("비고",item.get("note",""),"entry"),
        ], accent=C["items"]).show()
        if not r: return
        try:
            minq=float(r["안전재고"]); cost=float(r["단가(원)"])
        except ValueError:
            messagebox.showwarning("오류","숫자로 입력하세요."); return
        item.update({"name":r["품목명"],"type":r["분류"],"unit":r["단위"],
                     "min_qty":minq,"cost":cost,"note":r["비고"]})
        save(self.db); self.refresh_all()

    def delete_item(self):
        sel = self.item_tree.selection()
        if not sel: messagebox.showwarning("선택 필요","품목을 먼저 선택하세요."); return
        iid = sel[0]; name = self.db["items"][iid]["name"]
        if messagebox.askyesno("삭제 확인",f"'{name}'을(를) 삭제하시겠습니까?"):
            del self.db["items"][iid]; self.db["bom"].pop(iid,None)
            save(self.db); self.refresh_all()

    def edit_bom(self):
        sel = self.item_tree.selection()
        if not sel: messagebox.showwarning("선택 필요","품목을 먼저 선택하세요."); return
        iid = sel[0]; item = self.db["items"][iid]
        if item["type"] == "원자재":
            messagebox.showwarning("BOM 불가","원자재는 BOM을 설정할 수 없습니다."); return
        BomDialog(self.root, self.db, iid).show()
        save(self.db)

    # ── 생산 처리 탭 ─────────────────────────────────────────
    def _build_prod(self, f):
        section_header(f, "🏭  생산 처리 — BOM 기반 자동 원자재 차감", C["prod"])

        form = tk.Frame(f, bg=C["bg"], padx=20, pady=12)
        form.pack(fill=tk.X)

        def row(r, lbl, widget):
            tk.Label(form, text=lbl, font=("맑은 고딕",11),
                     bg=C["bg"], fg="#424242", anchor=tk.W, width=10).grid(
                row=r, column=0, pady=6, sticky=tk.W)
            widget.grid(row=r, column=1, padx=10, pady=6, sticky=tk.W)

        self.prod_item_var = tk.StringVar()
        self.prod_item_cb = ttk.Combobox(form, textvariable=self.prod_item_var,
                                         state="readonly", width=30, font=("맑은 고딕",11))
        self.prod_item_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_bom_preview())
        row(0,"생산 품목:", self.prod_item_cb)

        self.prod_qty_var = tk.StringVar(value="1")
        self.prod_qty_var.trace_add("write", lambda *_: self._refresh_bom_preview())
        qe = make_entry(form, self.prod_qty_var, width=14)
        row(1,"생산 수량:", qe)

        self.prod_note_var = tk.StringVar()
        ne = make_entry(form, self.prod_note_var, width=32)
        row(2,"비고:", ne)

        make_btn(form,"▶  생산 실행",self.do_produce,C["prod"],pad=(18,8)).grid(
            row=3, column=1, padx=10, pady=10, sticky=tk.W)

        # BOM 미리보기
        section_header(f, "📋  BOM 소요 자재 (실시간 미리보기)", C["prod"])
        cols = ("품목명","필요수량(1개당)","현재재고","단위","생산 가능 여부")
        self.bom_tree = self._make_tree(f, cols, [220,130,100,60,130])
        self.bom_tree.tag_configure("ok",   background=C["prod_bg"])
        self.bom_tree.tag_configure("lack", background=C["low"])

    def _refresh_bom_preview(self):
        t = self.bom_tree
        for r in t.get_children(): t.delete(r)
        name = self.prod_item_var.get()
        iid  = self._name_to_id(name)
        if not iid: return
        try:   pq = float(self.prod_qty_var.get() or 1)
        except: pq = 1
        bom = self.db["bom"].get(iid,[])
        if not bom:
            t.insert("","end",values=("(BOM 미설정)","-","-","-","-")); return
        for e in bom:
            mat = self.db["items"].get(e["material_id"])
            if not mat: continue
            need = e["qty"]*pq; stock = mat["quantity"]; ok = stock>=need
            t.insert("","end",values=(
                mat["name"], e["qty"], stock, mat["unit"],
                "✅ 가능" if ok else f"❌ 부족 ({stock}/{need:.1f})"),
                tags=("ok" if ok else "lack",))

    def do_produce(self):
        name = self.prod_item_var.get(); iid = self._name_to_id(name)
        if not iid: messagebox.showwarning("오류","생산 품목을 선택하세요."); return
        try:
            qty = float(self.prod_qty_var.get())
            if qty<=0: raise ValueError
        except: messagebox.showwarning("오류","생산 수량을 올바르게 입력하세요."); return
        bom = self.db["bom"].get(iid,[])
        if not bom: messagebox.showwarning("BOM 없음","BOM이 설정되지 않았습니다."); return
        shortage = []
        for e in bom:
            mat = self.db["items"].get(e["material_id"])
            if mat and mat["quantity"] < e["qty"]*qty:
                shortage.append(f"{mat['name']}: {mat['quantity']}{mat['unit']} / 필요 {e['qty']*qty}{mat['unit']}")
        if shortage:
            messagebox.showwarning("재고 부족","다음 원자재가 부족합니다:\n\n"+"\n".join(shortage)); return
        if not messagebox.askyesno("생산 확인",f"'{name}' {qty}{self.db['items'][iid]['unit']} 생산하시겠습니까?"):
            return
        note = self.prod_note_var.get()
        for e in bom:
            mat = self.db["items"].get(e["material_id"])
            if mat:
                used = e["qty"]*qty; mat["quantity"] -= used
                add_history(self.db,"원자재소비",e["material_id"],mat["name"],-used,f"{name} 생산용")
        self.db["items"][iid]["quantity"] += qty
        add_history(self.db,"생산완료",iid,name,qty,note)
        save(self.db); self.refresh_all()
        messagebox.showinfo("생산 완료",f"✅ '{name}' {qty}{self.db['items'][iid]['unit']} 생산 완료.")

    # ── 입출고 탭 ────────────────────────────────────────────
    def _build_io(self, f):
        # 입고 / 출고 나란히
        top = tk.Frame(f, bg=C["bg"])
        top.pack(fill=tk.X, padx=12, pady=8)

        for col_idx, (io_type, color, icon) in enumerate([
            ("입고", "#1565C0","📥"), ("출고","#C62828","📤")
        ]):
            pf = tk.LabelFrame(top, text=f"  {icon}  {io_type}  ",
                               font=("맑은 고딕",12,"bold"),
                               fg=color, bg=C["bg"], padx=14, pady=10,
                               relief=tk.GROOVE, bd=2)
            pf.grid(row=0, column=col_idx, padx=10, sticky=tk.NSEW)
            top.columnconfigure(col_idx, weight=1)

            item_var = tk.StringVar()
            qty_var  = tk.StringVar(value="1")
            note_var = tk.StringVar()

            if io_type == "입고":
                self.in_item_var=item_var; self.in_qty_var=qty_var; self.in_note_var=note_var
                self.in_item_cb = ttk.Combobox(pf, textvariable=item_var,
                                               state="readonly", width=26, font=("맑은 고딕",11))
                cb = self.in_item_cb
            else:
                self.out_item_var=item_var; self.out_qty_var=qty_var; self.out_note_var=note_var
                self.out_item_cb = ttk.Combobox(pf, textvariable=item_var,
                                                state="readonly", width=26, font=("맑은 고딕",11))
                cb = self.out_item_cb

            for r,(lbl,w) in enumerate([("품목:",cb),
                                         ("수량:",make_entry(pf,qty_var,14)),
                                         ("비고:",make_entry(pf,note_var,26))]):
                tk.Label(pf, text=lbl, font=("맑은 고딕",11),
                         bg=C["bg"], anchor=tk.W).grid(row=r,column=0,pady=5,sticky=tk.W)
                w.grid(row=r,column=1,padx=8,pady=5,sticky=tk.W)

            make_btn(pf,f"{icon}  {io_type} 처리",
                     lambda t=io_type: self.do_io(t),
                     color, pad=(16,7)).grid(row=3,column=1,pady=10,sticky=tk.W)

        # 최근 이력
        section_header(f,"🕐  최근 입출고 이력", C["io"])
        cols = ("일시","구분","품목명","수량","비고")
        self.io_hist_tree = self._make_tree(f, cols, [150,70,220,80,260])
        self.io_hist_tree.tag_configure("입고", background=C["in_bg"])
        self.io_hist_tree.tag_configure("출고", background=C["out_bg"])

    def do_io(self, io_type):
        if io_type == "입고":
            name=self.in_item_var.get(); qty_s=self.in_qty_var.get(); note=self.in_note_var.get()
        else:
            name=self.out_item_var.get(); qty_s=self.out_qty_var.get(); note=self.out_note_var.get()
        iid = self._name_to_id(name)
        if not iid: messagebox.showwarning("오류","품목을 선택하세요."); return
        try:
            qty = float(qty_s)
            if qty<=0: raise ValueError
        except: messagebox.showwarning("오류","수량을 올바르게 입력하세요."); return
        item = self.db["items"][iid]
        if io_type=="출고" and item["quantity"]<qty:
            messagebox.showwarning("재고 부족",f"재고 부족\n현재: {item['quantity']}{item['unit']}"); return
        delta = qty if io_type=="입고" else -qty
        item["quantity"] += delta
        add_history(self.db, io_type, iid, name, delta, note)
        save(self.db); self.refresh_all()
        messagebox.showinfo("완료",f"{'📥' if io_type=='입고' else '📤'} {io_type} 완료\n{name}  {qty}{item['unit']}")

    def refresh_io_hist(self):
        t = self.io_hist_tree
        for r in t.get_children(): t.delete(r)
        recent = [h for h in self.db["history"] if h["action"] in ("입고","출고")][-60:]
        for h in reversed(recent):
            t.insert("","end",values=(h["date"],h["action"],h["item_name"],
                                      h["qty"],h["note"]),tags=(h["action"],))

    # ── 이력 조회 탭 ─────────────────────────────────────────
    def _build_hist(self, f):
        section_header(f,"📜  전체 입출고 · 생산 이력", C["hist"])

        flt = tk.Frame(f, bg="#ECEFF1", pady=7)
        flt.pack(fill=tk.X)
        tk.Label(flt, text="  구분:", font=("맑은 고딕",11), bg="#ECEFF1").pack(side=tk.LEFT)
        self.hist_filter = tk.StringVar(value="전체")
        ttk.Combobox(flt, textvariable=self.hist_filter,
                     values=["전체","입고","출고","생산완료","원자재소비"],
                     state="readonly", width=12, font=("맑은 고딕",11)).pack(side=tk.LEFT,padx=6)
        self.hist_filter.trace_add("write", lambda *_: self.refresh_hist())

        tk.Label(flt, text="🔍 품목명:", font=("맑은 고딕",11), bg="#ECEFF1").pack(side=tk.LEFT, padx=(12,4))
        self.hist_search = tk.StringVar()
        self.hist_search.trace_add("write", lambda *_: self.refresh_hist())
        make_entry(flt, self.hist_search, width=20).pack(side=tk.LEFT, padx=4)

        self.hist_count_lbl = tk.Label(flt, font=("맑은 고딕",10),
                                       bg="#ECEFF1", fg="#546E7A")
        self.hist_count_lbl.pack(side=tk.RIGHT, padx=14)

        cols = ("일시","구분","품목명","수량","비고")
        self.hist_tree = self._make_tree(f, cols, [150,100,220,90,290])
        for act, bg in ACT_BG.items():
            self.hist_tree.tag_configure(act, background=bg)

    def refresh_hist(self):
        t = self.hist_tree
        for r in t.get_children(): t.delete(r)
        ft = self.hist_filter.get(); kw = self.hist_search.get().lower()
        cnt = 0
        for h in reversed(self.db["history"]):
            if ft!="전체" and h["action"]!=ft: continue
            if kw and kw not in h["item_name"].lower(): continue
            t.insert("","end",values=(h["date"],h["action"],h["item_name"],
                                      h["qty"],h["note"]),tags=(h["action"],))
            cnt+=1
        self.hist_count_lbl.config(text=f"총 {cnt}건")

    # ── 그래프 탭 ────────────────────────────────────────────
    def _build_graph(self, f):
        section_header(f,"📊  재고 분석 그래프", C["graph"])

        ctrl = tk.Frame(f, bg="#E0F2F1", pady=7)
        ctrl.pack(fill=tk.X)
        tk.Label(ctrl, text="  그래프 종류:", font=("맑은 고딕",11), bg="#E0F2F1").pack(side=tk.LEFT)
        self.graph_type = tk.StringVar(value="재고 현황 (막대)")
        opts = ["재고 현황 (막대)","재고 가치 비율 (파이)",
                "입출고 추이 (선)","분류별 재고 가치 (막대)"]
        cb = ttk.Combobox(ctrl, textvariable=self.graph_type, values=opts,
                          state="readonly", width=22, font=("맑은 고딕",11))
        cb.pack(side=tk.LEFT, padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_graph())
        make_btn(ctrl,"🔄 새로고침",self.refresh_graph,C["graph"],pad=(12,5)).pack(side=tk.LEFT,padx=8)

        self.graph_frame = tk.Frame(f, bg=C["bg"])
        self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        if not HAS_MPL:
            tk.Label(self.graph_frame,
                     text="matplotlib 미설치\n\n터미널에서 실행:\npip3.13 install matplotlib",
                     font=("맑은 고딕",13), fg="#C62828", bg=C["bg"]).pack(expand=True)

    def refresh_graph(self):
        if not HAS_MPL: return
        for w in self.graph_frame.winfo_children(): w.destroy()
        if self._mpl_canvas: plt.close("all"); self._mpl_canvas=None
        gmap = {
            "재고 현황 (막대)":     self._g_stock_bar,
            "재고 가치 비율 (파이)": self._g_value_pie,
            "입출고 추이 (선)":      self._g_io_trend,
            "분류별 재고 가치 (막대)":self._g_type_bar,
        }
        fig = gmap[self.graph_type.get()]()
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._mpl_canvas = canvas

    def _empty_fig(self, msg):
        fig, ax = plt.subplots(figsize=(8,4), facecolor="#F5F5F5")
        ax.text(0.5,0.5,msg,ha="center",va="center",fontsize=13,color="#9E9E9E",transform=ax.transAxes)
        ax.axis("off"); return fig

    def _g_stock_bar(self):
        items = list(self.db["items"].values())
        if not items: return self._empty_fig("등록된 품목이 없습니다.")
        cmap = {"원자재":"#42A5F5","반제품":"#FFCA28","완제품":"#66BB6A"}
        names  = [it["name"][:8] for it in items]
        qtys   = [it["quantity"] for it in items]
        minqs  = [it["min_qty"]  for it in items]
        colors = [cmap.get(it["type"],"#90A4AE") for it in items]
        fig, ax = plt.subplots(figsize=(10,4.5), facecolor="#FAFAFA")
        ax.set_facecolor("#F5F5F5")
        x = range(len(names))
        bars = ax.bar(x, qtys, color=colors, width=0.5, zorder=2, edgecolor="white", linewidth=0.8)
        ax.step([i-0.4 for i in x]+[len(x)-0.6], minqs+[minqs[-1]],
                color="#E53935", linewidth=2, linestyle="--", where="post", label="안전재고")
        for i,(q,m) in enumerate(zip(qtys,minqs)):
            if q<=m: bars[i].set_edgecolor("#E53935"); bars[i].set_linewidth(2.5)
        ax.set_xticks(list(x)); ax.set_xticklabels(names,rotation=30,ha="right",fontsize=9)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax.set_title("품목별 재고 현황",fontsize=13,fontweight="bold",pad=10,color="#212121")
        ax.set_ylabel("수량"); ax.grid(axis="y",linestyle="--",alpha=0.4,zorder=0)
        from matplotlib.patches import Patch
        handles = [Patch(color=c,label=t) for t,c in cmap.items()]
        handles += [plt.Line2D([0],[0],color="#E53935",linewidth=2,linestyle="--",label="안전재고")]
        ax.legend(handles=handles,fontsize=9,loc="upper right",framealpha=0.9)
        fig.tight_layout(); return fig

    def _g_value_pie(self):
        totals = defaultdict(float)
        for it in self.db["items"].values():
            totals[it["type"]] += it["quantity"]*it["cost"]
        if not any(totals.values()): return self._empty_fig("재고 가치 데이터가 없습니다.")
        labels=[k for k,v in totals.items() if v>0]
        values=[totals[k] for k in labels]
        cmap={"원자재":"#42A5F5","반제품":"#FFCA28","완제품":"#66BB6A"}
        clrs=[cmap.get(l,"#90A4AE") for l in labels]
        fig,ax=plt.subplots(figsize=(6,4.5),facecolor="#FAFAFA")
        wedges,texts,autos=ax.pie(values,labels=labels,colors=clrs,
            autopct=lambda p:f"{p:.1f}%\n({p/100*sum(values):,.0f}원)",
            startangle=140,pctdistance=0.78,
            wedgeprops={"edgecolor":"white","linewidth":2.5})
        for at in autos: at.set_fontsize(9)
        ax.set_title("분류별 재고 가치 비율",fontsize=13,fontweight="bold",pad=14,color="#212121")
        fig.tight_layout(); return fig

    def _g_io_trend(self):
        daily_in=defaultdict(float); daily_out=defaultdict(float)
        for h in self.db["history"]:
            d=h["date"][:10]
            if h["action"]=="입고":  daily_in[d]+=abs(h["qty"])
            elif h["action"]=="출고": daily_out[d]+=abs(h["qty"])
        all_dates=sorted(set(list(daily_in)+list(daily_out)))[-30:]
        if not all_dates: return self._empty_fig("입출고 이력이 없습니다.")
        ins=[daily_in.get(d,0) for d in all_dates]
        outs=[daily_out.get(d,0) for d in all_dates]
        fig,ax=plt.subplots(figsize=(10,4.5),facecolor="#FAFAFA")
        ax.set_facecolor("#F5F5F5")
        ax.plot(all_dates,ins, marker="o",color="#1E88E5",label="입고",linewidth=2,markersize=5)
        ax.plot(all_dates,outs,marker="s",color="#E53935",label="출고",linewidth=2,markersize=5)
        ax.fill_between(all_dates,ins, alpha=0.12,color="#1E88E5")
        ax.fill_between(all_dates,outs,alpha=0.12,color="#E53935")
        ax.set_title("입출고 추이 (최근 30일)",fontsize=13,fontweight="bold",pad=10,color="#212121")
        ax.set_ylabel("수량"); ax.legend(fontsize=10,framealpha=0.9)
        ax.grid(linestyle="--",alpha=0.4)
        plt.xticks(rotation=35,ha="right",fontsize=8)
        fig.tight_layout(); return fig

    def _g_type_bar(self):
        type_items=defaultdict(list)
        for it in self.db["items"].values(): type_items[it["type"]].append(it)
        if not type_items: return self._empty_fig("등록된 품목이 없습니다.")
        cmap={"원자재":"#42A5F5","반제품":"#FFCA28","완제품":"#66BB6A"}
        x_labels=list(type_items.keys())
        values=[sum(it["quantity"]*it["cost"] for it in type_items[t]) for t in x_labels]
        clrs=[cmap.get(t,"#90A4AE") for t in x_labels]
        fig,ax=plt.subplots(figsize=(7,4.5),facecolor="#FAFAFA")
        ax.set_facecolor("#F5F5F5")
        bars=ax.bar(x_labels,values,color=clrs,width=0.4,edgecolor="white",linewidth=1.5)
        for bar,val in zip(bars,values):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(values)*0.01,
                    f"{val:,.0f}원",ha="center",va="bottom",fontsize=10,fontweight="bold")
        ax.set_title("분류별 재고 가치",fontsize=13,fontweight="bold",pad=10,color="#212121")
        ax.set_ylabel("재고 가치 (원)")
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x,_:f"{x:,.0f}"))
        ax.grid(axis="y",linestyle="--",alpha=0.4)
        fig.tight_layout(); return fig

    # ── 공통 유틸 ────────────────────────────────────────────
    def _make_tree(self, parent, cols, widths):
        frame = tk.Frame(parent, bg=C["bg"])
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        style = ttk.Style()
        style.configure("Treeview", font=("맑은 고딕",10), rowheight=24)
        style.configure("Treeview.Heading", font=("맑은 고딕",10,"bold"), background="#CFD8DC")
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col,w in zip(cols,widths):
            tree.heading(col,text=col)
            tree.column(col,width=w,anchor=tk.CENTER)
        tree.column(cols[0],anchor=tk.W)
        sb = ttk.Scrollbar(frame,orient=tk.VERTICAL,command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        sb.pack(side=tk.RIGHT,fill=tk.Y)
        return tree

    def _name_to_id(self, name):
        for iid,item in self.db["items"].items():
            if item["name"]==name: return iid
        return None

    def _refresh_combos(self):
        all_n  = [v["name"] for v in self.db["items"].values()]
        prod_n = [v["name"] for v in self.db["items"].values() if v["type"] in ("반제품","완제품")]
        self.prod_item_cb["values"] = prod_n
        self.in_item_cb["values"]   = all_n
        self.out_item_cb["values"]  = all_n

    def refresh_all(self):
        self.refresh_dash()
        self.refresh_items()
        self.refresh_io_hist()
        self.refresh_hist()
        self._refresh_combos()
        self._refresh_bom_preview()


# ── BOM 편집 다이얼로그 ──────────────────────────────────────
class BomDialog(tk.Toplevel):
    def __init__(self, parent, db, item_id):
        super().__init__(parent)
        self.db=db; self.item_id=item_id
        item=db["items"][item_id]
        self.title(f"BOM 설정  —  {item['name']}")
        self.geometry("580x460")
        self.configure(bg=C["bg"])
        self.grab_set(); self.resizable(False,True)
        self._build(); self._refresh()

    def _build(self):
        hf = tk.Frame(self, bg=C["items"])
        hf.pack(fill=tk.X)
        tk.Label(hf, text=f"  ⚙  BOM 설정  —  {self.db['items'][self.item_id]['name']}",
                 font=("맑은 고딕",12,"bold"), bg=C["items"], fg="white", pady=10).pack(anchor=tk.W)

        cols=("품목명","분류","단위","소요수량(1개당)")
        frame=tk.Frame(self, bg=C["bg"])
        frame.pack(fill=tk.BOTH,expand=True,padx=12,pady=8)
        self.tree=ttk.Treeview(frame,columns=cols,show="headings",height=8)
        for col,w in zip(cols,[190,70,60,130]):
            self.tree.heading(col,text=col)
            self.tree.column(col,width=w,anchor=tk.CENTER)
        self.tree.column("품목명",anchor=tk.W)
        self.tree.pack(fill=tk.BOTH,expand=True)

        cands = {iid:v for iid,v in self.db["items"].items()
                 if iid!=self.item_id and v["type"] in ("원자재","반제품")}
        self._cand=cands
        names=[v["name"] for v in cands.values()]

        af=tk.Frame(self,bg="#E8EAF6",padx=10,pady=8)
        af.pack(fill=tk.X)
        tk.Label(af,text="품목:",font=("맑은 고딕",11),bg="#E8EAF6").pack(side=tk.LEFT)
        self.sel_var=tk.StringVar()
        ttk.Combobox(af,textvariable=self.sel_var,values=names,
                     state="readonly",width=18,font=("맑은 고딕",11)).pack(side=tk.LEFT,padx=6)
        tk.Label(af,text="소요량:",font=("맑은 고딕",11),bg="#E8EAF6").pack(side=tk.LEFT,padx=(10,4))
        self.qty_var=tk.StringVar(value="1")
        make_entry(af,self.qty_var,8).pack(side=tk.LEFT,padx=4)
        make_btn(af,"추가",self._add,"#1565C0",pad=(10,5)).pack(side=tk.LEFT,padx=6)
        make_btn(af,"선택삭제",self._del,"#C62828",pad=(10,5)).pack(side=tk.LEFT)

        make_btn(self,"💾  저장 후 닫기",self.destroy,C["items"],pad=(16,8)).pack(pady=10)

    def _name_to_id(self,name):
        for iid,v in self._cand.items():
            if v["name"]==name: return iid
        return None

    def _refresh(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        for e in self.db["bom"].get(self.item_id,[]):
            mat=self.db["items"].get(e["material_id"])
            if mat:
                self.tree.insert("","end",iid=e["material_id"],
                                 values=(mat["name"],mat["type"],mat["unit"],e["qty"]))

    def _add(self):
        mid=self._name_to_id(self.sel_var.get())
        if not mid: messagebox.showwarning("오류","품목을 선택하세요.",parent=self); return
        try:
            qty=float(self.qty_var.get())
            if qty<=0: raise ValueError
        except: messagebox.showwarning("오류","소요량을 올바르게 입력하세요.",parent=self); return
        bom=self.db["bom"].setdefault(self.item_id,[])
        for e in bom:
            if e["material_id"]==mid: e["qty"]=qty; self._refresh(); return
        bom.append({"material_id":mid,"qty":qty})
        self._refresh()

    def _del(self):
        sel=self.tree.selection()
        if not sel: return
        mid=sel[0]
        self.db["bom"][self.item_id]=[e for e in self.db["bom"].get(self.item_id,[])
                                       if e["material_id"]!=mid]
        self._refresh()

    def show(self): self.wait_window()


if __name__ == "__main__":
    root = tk.Tk()
    MfgApp(root)
    root.mainloop()
