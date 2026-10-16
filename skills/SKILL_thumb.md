---
name: tieu-de-thumb-audio-hoc-duong
description: Đọc kịch bản truyện audio học đường tiếng Việt (dòng hoa khôi - trà xanh - học sinh mới - ảo tưởng - cả lớp), dán trực tiếp hoặc tải lên dạng file docx/txt, rồi sinh trọn gói phần đóng gói video YouTube: 10 tiêu đề tối ưu CTR, text thumbnail 3 tầng, VÀ mô tả video đầy đủ gồm tóm tắt nội dung, mốc thời gian, hashtag, disclaimer song ngữ. Dựa trên công thức giải mã từ số liệu thật của Bảo Bối Audio, Mạn Mạn Audio, Tố Tố Audio. Là khâu cuối nối tiếp skill kichban-audio-hocduong. Dùng skill này BẤT CỨ KHI NÀO người dùng đã có kịch bản và nói "đặt tiêu đề", "làm tiêu đề cho bộ này", "viết thumbnail", "text thumb", "tiêu đề viral", "đặt tên video", "viết mô tả video", "làm description", "đóng gói video này", hoặc gọi /tieu-de-audio. Cũng kích hoạt khi người dùng tải file kịch bản lên rồi hỏi "đặt tên sao cho nhiều view", "tiêu đề nào CTR cao", hoặc nói "làm phần tiêu đề đi", "làm phần mô tả đi". KHÔNG dùng cho kênh spiritual tiếng Nhật, Bible explainer, hay video short so sánh.
---

# Tiêu đề & Thumbnail — Truyện Audio Học Đường

Sinh trọn gói phần đóng gói cho video truyện audio dài 55–65 phút, ngách học đường Việt hóa. Đầu vào là kịch bản đã viết xong, dán trực tiếp hoặc tải lên dưới dạng file. Đầu ra là 10 tiêu đề xếp hạng, 3 phương án thumbnail, và mô tả video đầy đủ — copy dán được ngay, không cần sửa tay.

Đây là khâu cuối trong quy trình sản xuất. Khâu trước là viết kịch bản, do skill `kichban-audio-hocduong` đảm nhận. Kịch bản đến từ đó luôn theo khung 7 khối, nên vị trí các yếu tố cần trích là cố định và dễ tìm.

Ngách này CTR quyết định gần như toàn bộ kết quả. Cùng một kịch bản, tiêu đề đúng công thức và tiêu đề sai công thức chênh nhau 3 đến 6 lần lượt xem. Số liệu chứng minh nằm ở `references/du-lieu-doi-thu.md` — đọc file đó khi cần dẫn chứng cụ thể hoặc khi người dùng hỏi tại sao chọn từ khóa này thay vì từ khóa kia.

## Quy trình bốn bước

**Bước 1 — Đọc kịch bản, trích đúng bốn thứ.** Không tóm tắt cốt truyện. Chỉ tìm:

- Nhân vật gây rắc rối là ai (không phải nhân vật chính "tôi")
- Hành động phi lý lớn nhất của nhân vật đó
- Ai hoặc cái gì bị kéo vào (cả lớp, cả trường, cả ký túc, hay chỉ một người)
- Bối cảnh nghiêm túc nếu có (kỳ thi, quân sự, lễ tốt nghiệp, đại hội thể thao, khai giảng)

**Cách đọc kịch bản dài hiệu quả.** Kịch bản ngách này dài 16.000–18.500 từ. Không cần đọc hết, và không nên đọc hết.

Kịch bản viết theo khung 7 khối luôn đặt toàn bộ bốn yếu tố trên vào **khối hook — khoảng 150 từ đầu tiên**. Đọc đoạn đó là đủ để làm tiêu đề và thumbnail.

Đọc thêm hai chỗ nữa, chỉ để viết phần mô tả:
- Khoảng 60–70% độ dài bài: đây là vùng cao trào, lấy ý cho câu treo lửng
- Vài trăm từ cuối: xác nhận kết cục, để chắc chắn không viết mô tả sai hướng

**Nếu người dùng tải lên file** (.docx, .txt, .md), file nằm ở `/mnt/user-data/uploads`. Với .docx dùng python-docx. Với file dài, chỉ trích ba vùng nêu trên thay vì in toàn bộ ra:

```python
import docx
d = docx.Document('/mnt/user-data/uploads/[tên file]')
t = ' '.join(p.text for p in d.paragraphs if p.text.strip())
w = t.split()
print('Tổng:', len(w), 'từ')
print('HOOK:', ' '.join(w[:200]))
print('CAO TRÀO:', ' '.join(w[int(len(w)*0.65):int(len(w)*0.65)+200]))
print('KẾT:', ' '.join(w[-200:]))
```

Tổng số từ cũng cần cho phần mô tả: chia cho 295 ra số phút audio ước tính.

**Bước 2 — Ánh xạ nhân vật vào chủ thể chuẩn.** Bảng chủ thể bên dưới. Nhân vật trong kịch bản gần với chủ thể nào nhất thì dùng đúng nhãn đó, không dùng tên riêng nhân vật.

**Bước 3 — Ráp công thức.** Bốn mẫu câu bên dưới, chọn mẫu khớp nhất với hành động.

**Bước 4 — Xuất 10 tiêu đề xếp hạng, kèm 3 phương án thumbnail.** Đúng định dạng ở mục Output.

**Bước 5 — Viết mô tả video.** Xem mục Mô tả video bên dưới. Phần này dùng lại chính bốn yếu tố đã trích ở bước 1, nên không cần đọc lại kịch bản.

## Bảng chủ thể — dùng đúng nhãn, không dùng tên riêng

Xếp theo hiệu suất thật đo được trên các kênh cùng ngách:

| Nhãn | Hiệu suất | Dùng khi |
|---|---|---|
| **TRÀ XANH** | Cao nhất | Nhân vật giả nai, thảo mai, hại người sau lưng |
| **HỌC SINH MỚI** | Rất cao | Người mới chuyển đến, mới nhập học |
| **HOA KHÔI** | Cao, nền tảng | Nữ sinh nổi tiếng nhất lớp/trường |
| **BẢO BỐI / BÉ CƯNG / CỤC CƯNG** | Rất cao | Nhân vật được cả nhóm cưng chiều |
| **TRỌNG SINH** | Cao, ít cạnh tranh | Truyện có yếu tố sống lại, quay về quá khứ |
| **THIÊN KIM / TIỂU THƯ** | Trung bình | Con nhà giàu |
| **LỚP TRƯỞNG / TRÙM TRƯỜNG** | Trung bình | Nhân vật có quyền lực trong trường |
| ~~BẠN CÙNG PHÒNG~~ | **Thấp — tránh** | Xem cảnh báo bên dưới |

Có thể ghép hai nhãn để tăng lực: `TRỌNG SINH + HOA KHÔI`, `HỌC SINH MỚI + TRÀ XANH`.

## Bảng động từ — thứ tạo ra cảm xúc bực tức

Cơ chế giữ chân của ngách này không phải tò mò mà là **bực tức có mục tiêu**. Người xem phải ghét nhân vật ngay từ tiêu đề, rồi ở lại chờ khoảnh khắc kẻ đó bị vả mặt. Động từ trung tính giết chết cơ chế này.

**Nhóm mạnh nhất — ưu tiên tuyệt đối:**
`ẢO TƯỞNG` · `TỰ NHẬN` · `TỰ XƯNG` · `ĐÒI` · `BẮT` · `ÉP` · `BỊP` · `LỪA` · `ĐỔ OAN` · `TUNG TIN` · `CƯỚP`

**Nhóm khá:**
`GIẢ LÀM` · `LÉN` · `VU OAN` · `ĐÒI THAY` · `NHỜ` · `MƯỢN`

**Nhóm yếu — chỉ dùng khi không còn cách nào:**
`thích` · `nói` · `chuẩn bị` · `quan tâm` · `tôn thờ` · `tốt bụng`

## Bốn mẫu công thức

**Mẫu A — Ảo tưởng bản thân** (mạnh nhất, dùng khi nhân vật tự đề cao)
```
[CHỦ THỂ] + ẢO TƯỞNG/TỰ NHẬN MÌNH LÀ + [danh xưng đẹp phi lý]
```
Ví dụ thật đạt 568K: HỌC SINH MỚI TỰ NHẬN MÌNH LÀ MỸ NHÂN TUYỆT TRẦN

**Mẫu B — Áp đặt lên tập thể** (dùng khi hành động kéo cả lớp vào)
```
[CHỦ THỂ] + ĐÒI/BẮT/ÉP + CẢ LỚP + [hành động phi lý]
```
Ví dụ thật đạt 138K: HOA KHÔI LỚP BẮT CẢ LỚP MẶC VÁY REN THAM GIA ĐẠI HỘI THỂ THAO

**Mẫu C — Phi lý trong bối cảnh nghiêm túc** (mạnh nhờ tương phản)
```
[CHỦ THỂ] + [hành động bừa bãi] + TRONG/VÀO + [KỲ THI / QUÂN SỰ / LỄ TỐT NGHIỆP]
```
Ví dụ thật đạt 76K: HOA KHÔI MẶC VÁY CƯỚI ĐI THI CUỐI KỲ

**Mẫu D — Đòi vị trí của nhân vật chính** (tạo đối kháng trực tiếp)
```
[CHỦ THỂ] + ĐÒI THAY/CƯỚP + TÔI + [vị trí hoặc người]
```
Ví dụ thật đạt 61K: TRÀ XANH ĐÒI THAY TÔI LÀM LỚP TRƯỞNG

## Cảnh báo — sáu thứ làm rớt view

**1. Không dùng "BẠN CÙNG PHÒNG" làm chủ thể chính.** Trên cùng một kênh, cùng thumbnail, cùng giọng đọc, nhóm tiêu đề "bạn cùng phòng" trung bình 10N view còn nhóm "cả lớp / hoa khôi" trung bình 36N. Chênh 3,6 lần. Quy mô 2 người luôn thua quy mô tập thể. Nếu kịch bản đúng là chuyện bạn cùng phòng, hãy tìm góc nào đó kéo cả ký túc hoặc cả lớp vào, hoặc đổi nhãn chủ thể sang TRÀ XANH.

**2. Không dùng tên riêng nhân vật.** "Tiểu Vũ đòi làm lớp trưởng" vô nghĩa với người chưa xem. Nhãn chủ thể mới là thứ người xem nhận diện.

**3. Không đặt câu hỏi.** "Chuyện gì xảy ra khi hoa khôi..." làm loãng lực. Tiêu đề ngách này luôn là câu khẳng định.

**4. Không spoil cú lật.** Tiêu đề chỉ nêu tình huống gây bực, không nêu kết quả. "Trà xanh đòi làm lớp trưởng rồi bị đuổi học" giết sạch lý do xem tiếp.

**5. Không quá 12 từ.** Thumbnail chỉ chứa được chừng đó. Dài hơn là bị cắt trên mobile.

**6. Không dùng dấu chấm than hay emoji trong tiêu đề.** Không kênh nào trong ngách dùng, và nó làm tiêu đề trông rẻ.

## Text thumbnail 3 tầng

Bố cục chuẩn của ngách: nền hồng pastel, ảnh nhân vật nữ một bên, khối chữ bên còn lại chia 3 dòng. Chữ VIẾT HOA TOÀN BỘ.

**Tầng 1 — Chủ thể.** Màu đen hoặc hồng đậm. 2–4 chữ.
**Tầng 2 — Hành động.** Màu ĐỎ, đây là dòng bắt mắt nhất, phải chứa động từ mạnh. 3–5 chữ.
**Tầng 3 — Đối tượng chịu tác động.** Màu đen. 2–5 chữ.

Tổng ba tầng không quá 14 chữ. Mỗi dòng không quá 5 chữ, vì dài hơn thì cỡ chữ phải giảm và trên mobile sẽ không đọc được.

Ví dụ:
```
Tầng 1 (đen):  HOA KHÔI LỚP
Tầng 2 (đỏ):   BẮT CẢ LỚP MẶC VÁY
Tầng 3 (đen):  NGÀY QUÂN SỰ
```

Nếu tiêu đề có yếu tố con số hoặc tiền bạc, đẩy con số lên tầng 2 màu đỏ — con số trong thumbnail tăng CTR rõ rệt (`HOA KHÔI ĐẶT 1000 SUẤT GÀ RÁN` đạt 27K trên kênh chỉ 3,46K sub).

## Định dạng tiêu đề đầy đủ khi đăng

```
Full Audio || [TIÊU ĐỀ VIẾT HOA] | [Tên Kênh] #audio #truyenaudio
```

Phần trước dấu `|` là thứ hiển thị trên mobile — dồn toàn bộ từ khóa mạnh vào đó. Hashtag luôn để cuối, không chèn giữa.

## Mô tả video

### Phần tóm tắt nội dung — thứ khó nhất, làm kỹ

Đây không phải tóm tắt cốt truyện. Đây là **mồi câu lần hai**: người xem đã bấm vào vì tiêu đề, giờ họ đọc mô tả để quyết định có nghe hết 60 phút hay không.

Ba câu, theo đúng thứ tự này:

**Câu 1 — Dựng tình huống gây bực.** Nêu nhân vật gây rắc rối đang làm gì quá đáng. Viết ở thì hiện tại, ngôi thứ nhất hoặc thứ ba đều được.

**Câu 2 — Đẩy mức độ leo thang.** Cho thấy chuyện không dừng lại mà còn tệ hơn, và nhân vật chính đang chịu thiệt.

**Câu 3 — Treo lửng.** Gợi rằng sắp có gì đó thay đổi, nhưng tuyệt đối không nói kết quả. Câu này thường bắt đầu bằng "Nhưng...", "Cho đến khi...", "Không ai ngờ...".

Ví dụ mẫu:
```
Cả lớp đều biết hoa khôi Lâm Nhi thích khoe khoang, nhưng
không ai ngờ cô ta dám đứng lên tuyên bố sẽ bao trọn chuyến
du lịch hè cho bốn mươi con người.

Tiền đặt cọc thu xong, lịch trình lên xong, ảnh đăng khắp
nhóm lớp — rồi ba ngày trước khi khởi hành, cô ta biến mất,
và người bị cả lớp quay sang chất vấn lại là tôi.

Cho đến buổi họp lớp hôm ấy, khi tôi mở chiếc điện thoại ra
trước mặt tất cả mọi người...
```

Bốn điều cấm ở phần này:

- **Không tiết lộ cú lật.** Nếu người đọc biết kết cục, họ không cần nghe.
- **Không dùng tên riêng nhân vật ở câu đầu** nếu tên đó chưa xuất hiện trong tiêu đề — người đọc chưa biết ai với ai.
- **Không viết quá 3 câu.** Trên mobile chỉ hiện được chừng đó trước nút "xem thêm".
- **Không viết kiểu review** ("Đây là câu chuyện cảm động về...", "Truyện kể về một cô gái..."). Viết như đang kể, không như đang giới thiệu.

### Mốc thời gian

Bắt buộc có. Video ngách này dài 55–65 phút; không có mốc thì người nghe chán ở phút thứ 5 sẽ thoát hẳn, có mốc thì họ nhảy tới đoạn cao trào và ở lại — YouTube tính đó là watch time hợp lệ.

Chia **7 mốc**, khớp với 7 khối của kịch bản. Với video 60 phút, vị trí ước tính:

```
00:00  [tên gợi tò mò lấy từ hook]
02:00  [nhân vật chính vào cuộc]
09:00  [kẻ xấu ra mặt]
23:00  [lần đụng độ đầu tiên]
38:00  [tình thế xấu nhất]
48:00  [cú lật]
57:00  Kết
```

Quy tắc đặt tên: **gợi tò mò**, không đặt kiểu mục lục.

- Tốt: `38:00 Cả lớp quay lưng`
- Tồi: `38:00 Phần 4`

Mốc cuối luôn trung tính (`Kết`), không spoil. Mốc cú lật cũng không được nêu kết quả — đặt kiểu `48:00 Sự thật được đưa ra` chứ không phải `48:00 Hoa khôi bị đuổi học`.

Vị trí trên là ước tính theo tỉ lệ 7 khối. Xuất kèm chỗ trống `[XX:XX]` bên cạnh để người dùng chỉnh lại sau khi dựng xong, vì tốc độ voice AI mỗi lần một khác.

### Hashtag

Ba hashtag đầu là thứ YouTube dùng để phân loại. Luôn đặt theo thứ tự: rộng → ngách → cụ thể.

```
#truyenaudio #audio #truyenngontinh #hocduong #trongsinh
```

Thêm 1–2 hashtag khớp chủ thể của truyện: `#hoakhoi` `#traxanh` `#baothu` `#thienkim`. Tối đa 7 hashtag, nhiều hơn YouTube sẽ bỏ qua toàn bộ.

### Disclaimer

Giữ nguyên khối song ngữ ở mục Output. Phần này viết cho bộ phận review kiếm tiền của YouTube, không viết cho người xem — nên không cần hay, chỉ cần đủ ba ý: nội dung hư cấu, audio là bản gốc tự sản xuất, hình ảnh chỉ là minh họa bổ trợ.

Lưu ý quan trọng: câu tuyên bố bản quyền audio chỉ có giá trị bảo vệ khi kịch bản là bản gốc do kênh viết. Nếu người dùng đang dùng kịch bản dịch từ nguồn khác, nhắc họ một câu ngắn rằng disclaimer này không thay thế được việc có bản quyền thật.

## Output — giao đúng khối này, không thêm lời dẫn

```
TÓM LƯỢC KỊCH BẢN
Chủ thể: ...
Hành động: ...
Quy mô: ...
Bối cảnh: ...

10 TIÊU ĐỀ (xếp theo dự đoán CTR)
1. ...
2. ...
...
10. ...

TOP 3 KHUYẾN NGHỊ
Chọn 1: ... — lý do một dòng
Chọn 2: ... — lý do một dòng
Chọn 3: ... — lý do một dòng

TEXT THUMBNAIL

Phương án 1 (theo tiêu đề số 1)
Tầng 1 (đen): ...
Tầng 2 (đỏ): ...
Tầng 3 (đen): ...

Phương án 2 (theo tiêu đề số 2)
Tầng 1 (đen): ...
Tầng 2 (đỏ): ...
Tầng 3 (đen): ...

Phương án 3 (theo tiêu đề số 3)
Tầng 1 (đen): ...
Tầng 2 (đỏ): ...
Tầng 3 (đen): ...

TIÊU ĐỀ ĐẦY ĐỦ KHI ĐĂNG
Full Audio || ... | ... #audio #truyenaudio

MÔ TẢ VIDEO (copy nguyên khối dưới đây)
```

Sau đó xuất tiếp khối mô tả, dùng tên kênh người dùng đã cho (nếu chưa biết, dùng `[TÊN KÊNH]` để họ thay):

```
🌸 Truyện audio full: [TIÊU ĐỀ ĐÃ CHỌN]

Thể loại: học đường, ngôn tình, drama, [thể loại phụ]
Thời lượng: [XX] phút | Giọng đọc: [TÊN KÊNH]

📖 NỘI DUNG

[Câu 1 — dựng tình huống gây bực]

[Câu 2 — leo thang, nhân vật chính chịu thiệt]

[Câu 3 — treo lửng, không spoil]

⏱️ MỐC THỜI GIAN
00:00 [tên mốc lấy từ hook]
02:00 [nhân vật chính vào cuộc]
09:00 [kẻ xấu ra mặt]
23:00 [lần đụng độ đầu tiên]
38:00 [tình thế xấu nhất]
48:00 [cú lật, không nêu kết quả]
57:00 Kết

🎧 Nghe thêm truyện cùng thể loại: [link playlist]
🔔 Đăng ký kênh để nghe truyện mới mỗi ngày: [link kênh]

━━━━━━━━━━━━━━━━━━━━

⚠️ MIỄN TRỪ TRÁCH NHIỆM

Đây là câu chuyện hư cấu hoàn toàn, được sản xuất dưới định dạng kể chuyện bằng audio nhằm mục đích giải trí.

Mọi nhân vật, tình tiết, tổ chức và hoàn cảnh trong truyện đều là hư cấu, không nhằm ám chỉ bất kỳ cá nhân, tổ chức hay sự kiện có thật nào.

Giá trị cốt lõi của video nằm ở phần audio kể chuyện do [TÊN KÊNH] sản xuất. Hình ảnh chỉ đóng vai trò minh họa bổ trợ.

Bản quyền phần audio thuộc về [TÊN KÊNH]. Vui lòng không sao chép, đăng lại hoặc sử dụng lại dưới bất kỳ hình thức nào.

━━━━━━━━━━━━━━━━━━━━

DISCLAIMER (English)

This is an entirely fictional story produced in an audio storytelling format for entertainment purposes.

All characters, details, organizations, and circumstances in this story are fictional and are not intended to represent any real individuals, entities, or actual events.

The core value of this video comes from the original narrated audio produced by [TÊN KÊNH]. Visual elements are supplementary materials only.

The audio copyright belongs to [TÊN KÊNH]. Please do not copy, repost, or reuse it in any form.

#truyenaudio #audio #truyenngontinh #hocduong #trongsinh
```

Trong 10 tiêu đề, phân bổ: 3 tiêu đề mẫu A, 3 mẫu B, 2 mẫu C, 2 mẫu D. Nếu kịch bản không hợp mẫu nào đó thì dồn số lượng sang mẫu hợp hơn, nhưng luôn đủ 10.

## Kiểm tra trước khi giao

1. Có tiêu đề nào dùng "bạn cùng phòng" làm chủ thể chính không? Nếu có, viết lại.
2. Mỗi tiêu đề có ít nhất một động từ thuộc nhóm mạnh chưa?
3. Có tiêu đề nào dùng tên riêng nhân vật không?
4. Có tiêu đề nào spoil kết quả không?
5. Tiêu đề nào dài quá 12 từ không?
6. Ít nhất 5 trong 10 tiêu đề có chứa CẢ LỚP hoặc CẢ TRƯỜNG chưa?
7. Tầng 2 của mọi thumbnail có động từ mạnh chưa? Mỗi dòng có quá 5 chữ không?
8. Có dấu chấm than, emoji, hay dấu hỏi lọt vào không?

Với phần mô tả video:

9. Phần NỘI DUNG có đúng 3 câu không? Có spoil cú lật không?
10. Câu 3 có treo lửng thật sự chưa, hay đã lỡ nói ra kết quả?
11. Tên mốc thời gian có gợi tò mò không, hay đang đặt kiểu "Phần 1, Phần 2"?
12. Mốc cuối có lỡ spoil không?
13. Hashtag có quá 7 cái không?
14. Đã thay hết `[TÊN KÊNH]` bằng tên thật chưa (nếu người dùng đã cho biết)?
15. Thời lượng trong mô tả có khớp với số từ chia 295 không?
16. Mốc cú lật có lỡ nêu kết quả không?

## Khi người dùng chưa đưa kịch bản

Nếu người dùng gọi skill mà chưa dán kịch bản, hỏi ngắn gọn một câu duy nhất: xin kịch bản hoặc tóm tắt 3–5 câu về nhân vật gây rắc rối và hành động chính. Không hỏi thêm gì khác, không hỏi về giọng đọc, độ dài, hay đối tượng khán giả — những thứ đó không ảnh hưởng tới tiêu đề.
