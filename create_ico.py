"""
Windows .ico 아이콘 파일 생성 (PIL 없이 순수 파이썬)
"""
import struct, zlib, os, math

def make_png(size):
    """순수 파이썬으로 재고관리 아이콘 PNG 바이트 생성"""

    def chunk(name, data):
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    # 팔레트
    NAVY   = (26,  35, 126)
    BLUE   = (21, 101, 192)
    LBLUE  = (30, 136, 229)
    WHITE  = (255,255,255)
    YELLOW = (255,193,  7)
    LBLUE2 = (144,202,249)
    TRANS  = None  # 투명

    pixels = []
    cx = cy = size / 2
    r_out  = cx - 1

    for y in range(size):
        for x in range(size):
            dx = x - cx; dy = y - cy
            dist = math.sqrt(dx*dx + dy*dy)

            if dist > r_out:
                pixels.append(TRANS); continue

            # ─ 배경 그라디언트 (네이비→블루) ─
            t = dist / r_out
            r = int(BLUE[0]*(1-t) + LBLUE[0]*t)
            g = int(BLUE[1]*(1-t) + LBLUE[1]*t)
            b = int(BLUE[2]*(1-t) + LBLUE[2]*t)
            px = (r, g, b)

            # 외곽 테두리
            if dist > r_out - max(2, size*0.04):
                px = NAVY

            # ─ 큰 박스 (흰색) ─
            b1x1, b1y1 = size*0.18, size*0.44
            b1x2, b1y2 = size*0.65, size*0.74
            if b1x1 <= x <= b1x2 and b1y1 <= y <= b1y2:
                px = WHITE

            # ─ 큰 박스 뚜껑 ─
            lid_y1, lid_y2 = size*0.38, size*0.46
            lid_x1, lid_x2 = size*0.16, size*0.67
            if lid_x1 <= x <= lid_x2 and lid_y1 <= y <= lid_y2:
                px = WHITE

            # ─ 뚜껑 가운데 홈 ─
            notch_x1, notch_x2 = size*0.37, size*0.47
            notch_y1, notch_y2 = size*0.36, size*0.40
            if notch_x1 <= x <= notch_x2 and notch_y1 <= y <= notch_y2:
                px = (180,220,255)

            # ─ 작은 박스 (하늘색) ─
            b2x1, b2y1 = size*0.58, size*0.54
            b2x2, b2y2 = size*0.78, size*0.72
            if b2x1 <= x <= b2x2 and b2y1 <= y <= b2y2:
                px = LBLUE2
            b2l_y1, b2l_y2 = size*0.50, size*0.56
            if b2x1 <= x <= b2x2 and b2l_y1 <= y <= b2l_y2:
                px = LBLUE2

            # ─ 화살표 (위쪽, 노란색) ─
            aw = size*0.10
            ax1, ax2 = size*0.82 - aw/2, size*0.82 + aw/2
            ay_top, ay_bot = size*0.22, size*0.38
            # 삼각형
            tip_y = ay_top
            base_y = ay_top + aw
            if ay_top <= y <= base_y:
                half = aw/2 * (y - tip_y) / max(1, base_y - tip_y)
                if abs(x - size*0.82) <= half:
                    px = YELLOW
            # 막대
            bar_x1, bar_x2 = size*0.82 - aw*0.28, size*0.82 + aw*0.28
            if bar_x1 <= x <= bar_x2 and base_y <= y <= ay_bot:
                px = YELLOW

            # ─ 수평선 (데이터 느낌) ─
            for line_y in [size*0.82, size*0.87]:
                if abs(y - line_y) <= max(1, size*0.02) and size*0.18 <= x <= size*0.65:
                    alpha_factor = 1 - abs(y - line_y) / max(1, size*0.02)
                    if alpha_factor > 0.3:
                        px = (180,210,255)

            pixels.append(px)

    # PNG 인코딩 (RGBA)
    raw = b""
    for y in range(size):
        raw += b"\x00"  # filter none
        for x in range(size):
            px = pixels[y*size+x]
            if px is None:
                raw += b"\x00\x00\x00\x00"
            else:
                raw += bytes([px[0], px[1], px[2], 255])

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # RGBA
    sig = b"\x89PNG\r\n\x1a\n"
    return (sig
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def create_ico(output_path):
    """여러 해상도를 포함한 .ico 파일 생성"""
    sizes = [16, 32, 48, 64, 128, 256]
    png_list = []

    print("  아이콘 크기 생성 중...")
    for s in sizes:
        print(f"    {s}x{s}...", end="", flush=True)
        png_data = make_png(s)
        png_list.append((s, png_data))
        print(" ✓")

    # ICO 헤더
    count = len(png_list)
    header = struct.pack("<HHH", 0, 1, count)

    # 디렉토리 항목 오프셋 계산
    dir_size = count * 16
    offset = 6 + dir_size

    directory = b""
    for s, png_data in png_list:
        sz = 0 if s == 256 else s  # 256은 0으로 표기
        directory += struct.pack(
            "<BBBBHHII",
            sz, sz,  # width, height
            0,       # color count (0 = no palette)
            0,       # reserved
            1,       # color planes
            32,      # bits per pixel
            len(png_data),
            offset
        )
        offset += len(png_data)

    # 파일 조합
    ico_data = header + directory
    for _, png_data in png_list:
        ico_data += png_data

    with open(output_path, "wb") as f:
        f.write(ico_data)

    size_kb = len(ico_data) / 1024
    print(f"  ✅ {output_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.ico")
    print("🎨 Windows 아이콘(.ico) 생성 중...")
    create_ico(out)
    print("완료!")
