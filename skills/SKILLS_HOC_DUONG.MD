---
name: kichban-audio-hocduong
description: Viết kịch bản truyện audio học đường tiếng Việt dài 16.000-18.500 từ (55-65 phút voiceover) theo khung 7 khối giải mã từ kênh Bảo Bối Audio, dòng hoa khôi - trà xanh - học sinh mới - ảo tưởng - cả lớp. Đầu vào linh hoạt: một dòng motif, một ý tưởng thô, hoặc một kịch bản/truyện tham chiếu (đọc để rút cấu trúc rồi viết truyện MỚI, không dịch lại), kèm bốn tham số tùy chọn để chống trùng lặp khi sản xuất hàng loạt. Output voiceover-ready, không markdown, không tiêu đề phần, không chú thích. Dùng skill này BẤT CỨ KHI NÀO người dùng nói "viết kịch bản truyện audio", "làm kịch bản cho video này", "viết truyện hoa khôi", "viết truyện trà xanh", "làm bộ mới", "viết cho tôi 16000 từ", "kịch bản 60 phút", hoặc gọi /kichban-audio. Cũng kích hoạt khi người dùng đưa một motif kiểu "hoa khôi bắt cả lớp làm X" rồi nói "làm đi", hoặc dán truyện tham chiếu rồi nói "viết bản của tôi". KHÔNG dùng cho kênh spiritual tiếng Nhật, Bible explainer, video short so sánh, hay dịch phụ đề.
---

# Kịch bản truyện audio học đường — 16.000+ từ

Viết kịch bản gốc cho video audio 55–65 phút, ngách học đường Việt hóa. Ngách này thắng bằng **watch time**, nên độ dài không phải tùy chọn mà là yêu cầu cứng.

Số liệu nền: Bảo Bối Audio viết 16.500–18.500 từ mỗi kịch bản, 19,2N sub, video top 568K. Mạn Mạn Audio cùng dòng, cùng motif, cùng phong cách thumbnail, nhưng viết 30–38 phút — chỉ 3,46N sub, top 137K. Biến số khác nhau lớn nhất là độ dài.

Chi tiết số liệu và ngân hàng motif nằm ở `references/cau-truc-va-motif.md`. Đọc file đó khi cần motif mới, khi cần dẫn chứng, hoặc khi người dùng hỏi tại sao viết theo cách này.

## Xử lý đầu vào

**Nếu người dùng đưa một dòng motif** (ví dụ: "hoa khôi bắt cả lớp mặc áo dài ngày quân sự") — vào việc ngay, không hỏi lại. Tự dựng nhân vật, bối cảnh, tình tiết.

**Nếu người dùng đưa truyện hoặc kịch bản tham chiếu tiếng Trung/Việt** — đọc để rút ra bốn thứ: motif gốc, kiểu xung đột, nhịp leo thang, kiểu cú lật. Sau đó **viết truyện hoàn toàn mới** với motif đó. Không giữ tên nhân vật, không giữ chuỗi tình tiết, không dịch câu nào. Nói với người dùng một dòng ngắn rằng đây là bản gốc dựng theo motif, rồi giao kịch bản.

**Nếu đầu vào quá mơ hồ** (chỉ nói "viết cho tôi một bộ") — hỏi đúng một câu: muốn chủ thể nào (hoa khôi / trà xanh / học sinh mới) và hành động phi lý là gì. Không hỏi thêm về giọng đọc, độ dài, hay khán giả.

## Bốn tham số tùy chọn

Người dùng có thể đưa thêm bốn tham số dưới đây để kiểm soát output. Nếu họ không đưa, tự chọn theo hướng dẫn mặc định và **báo lại một dòng ngắn** đã chọn gì, để lần sau họ biết mà chỉ định.

**1. Khung cú lật** — bốn khung nằm ở file reference: bằng chứng vật lý, thân phận bị lộ, nhân chứng đứng lên, tự sập bẫy. Mặc định: luân phiên, không dùng lại khung của bài trước. Đây là tham số quan trọng nhất khi sản xuất hàng loạt, vì trùng khung hai bài liên tiếp là khán giả nhận ra ngay và đoán trước được kết.

**2. Hoàn cảnh nhân vật chính** — chọn một trong bốn:
- Nghèo, gia đình lao động (đồng cảm cao nhất, nhưng đừng dùng quá 4 trong 10 bài)
- Học giỏi nhưng bị coi thường
- Khá giả nhưng giấu, không muốn dựa gia đình
- Có tài lẻ chưa ai biết (vẽ, hát, code, chụp ảnh)

Mặc định: luân phiên. Lặp lại cùng một hoàn cảnh nhiều bài liền làm khán giả chán nhân vật chính chứ không phải chán motif.

**3. Tuyến tình cảm** — ba mức:
- Không có: chỉ drama tập thể
- Mờ: có một nam sinh đứng về phía nhân vật chính ở khối 5, không tỏ tình, không hẹn hò
- Nhẹ: có tín hiệu tình cảm ở khối 6, dừng ở mức nắm tay hoặc một câu ngỏ ý

Mặc định: mờ. Không bao giờ vượt quá mức nhẹ, vì ngách này nhắm học sinh sinh viên và YouTube hạn chế quảng cáo với nội dung tình cảm đậm.

**4. Ràng buộc của voice AI** — nếu người dùng cho biết giọng đọc hoặc từ nào voice AI đọc sai, áp dụng:
- Giọng nữ trẻ: câu ngắn hơn, trung bình 15–17 từ
- Giọng nữ trung niên: chịu được câu 18–22 từ
- Từ voice AI đọc sai: tránh hoàn toàn, tìm từ đồng nghĩa

Mặc định: câu trung bình 19 từ, tránh từ Hán Việt hiếm và từ có nhiều dấu liên tiếp.

Cách người dùng thường đưa tham số, chấp nhận mọi định dạng:

```
/kichban-audio
Motif: hoa khôi bịa chuyện bị mất đồ
Cú lật: nhân chứng đứng lên
Nhân vật chính: học giỏi nhưng bị coi thường
Tình cảm: nhẹ
```

## Khung 7 khối — bám sát số từ

Tổng mục tiêu **16.000–18.500 từ**. Viết từng khối một, viết xong khối này mới sang khối sau. Không viết một mạch, vì viết một mạch luôn ra ngắn hơn mục tiêu.

**Khối 1 — Hook drama** (100–150 từ)
Vào thẳng, không chào kênh, không dẫn nhập. Nêu ngay hành động phi lý của kẻ gây rắc rối, ở ngôi thứ nhất. Dùng lại đúng cụm từ sẽ nằm trong tiêu đề video. Kết khối bằng một câu cho thấy nhân vật chính sẽ không nhịn.

Mẫu nhịp: `[Bối cảnh một câu] + [Yêu sách vô lý, liệt kê 3 vế] + [Thái độ của tôi]`

**Khối 2 — Dựng bối cảnh** (1.500–2.000 từ)
Giới thiệu nhân vật chính: tên, hoàn cảnh, mục tiêu cụ thể (học bổng, suất thực tập, kỳ thi). Tả không gian bằng chi tiết giác quan — mùi, âm thanh, ánh sáng, thời tiết. Đưa vào một nhân vật phụ thân thiết để làm người kể bối cảnh cho khán giả.

Đây là khối bơm chữ chính. Đừng vội, tả kỹ.

**Khối 3 — Kẻ xấu ra mặt** (3.000–4.000 từ)
Nhân vật phản diện xuất hiện và áp đặt luật lệ vô lý. Có đám đông chứng kiến. Nhân vật phụ giải thích cho nhân vật chính (và khán giả) rằng kẻ này có thế lực gì, ai đã từng chống lại và kết cục ra sao.

Nhân vật chính phản ứng nhẹ, chưa đánh trả — để dành cho sau.

**Khối 4 — Leo thang** (4.000–5.000 từ)
Ba đến bốn lần đụng độ, mỗi lần nặng hơn lần trước. Công thức leo thang:

1. Lần một: gây khó chịu (nói xấu, cô lập)
2. Lần hai: gây thiệt hại nhỏ (phá đồ, đổ oan chuyện nhỏ)
3. Lần ba: gây thiệt hại lớn (phá đồ án, vu khống trước tập thể)
4. Lần bốn (tùy chọn): chạm tới người thân của nhân vật chính

Mỗi lần đụng độ phải có **thoại**. Đây là khối nhiều đối thoại nhất.

**Khối 5 — Cao trào và lật kèo** (3.000–4.000 từ)
Kẻ xấu bị vạch trần **trước đám đông**. Đây là đoạn khán giả chờ suốt 40 phút, viết kỹ nhất.

Ba yếu tố bắt buộc:
- Có bằng chứng cụ thể (tin nhắn, camera, người làm chứng, bài thi)
- Có nhân vật quyền lực xác nhận (giáo viên, hiệu trưởng, phụ huynh, nhân vật giàu có)
- Có phản ứng của đám đông (xì xào, quay video, đứng về phía nhân vật chính)

Nhân vật chính nói một đoạn đanh thép. Đoạn này nên dài 150–250 từ, là câu quote người nghe sẽ nhớ.

**Khối 6 — Hậu quả** (2.000–2.500 từ)
Kẻ xấu nhận kết cục cụ thể: bị kỷ luật, mất danh hiệu, bị cả lớp xa lánh, gia đình mất mặt. Nhân vật chính đạt được mục tiêu đã nêu ở Khối 2 — học bổng, suất thực tập, vị trí nhất khối.

Nếu có tuyến tình cảm nhẹ thì đóng ở đây, giữ mức trong sáng.

**Khối 7 — Kết** (100–200 từ)
Một đoạn chiêm nghiệm ngắn về bài học, giọng nhẹ nhàng. Không giáo huấn dài dòng.

Sau đó là câu CTA cố định của kênh (người dùng tự thêm khi dựng video, hoặc nếu họ đã cho biết câu CTA thì viết vào).

## Quy tắc văn phong

**Câu ngắn, trung bình 15–20 từ.** Kịch bản gốc của Bảo Bối trung bình 19,4 từ mỗi câu. Câu dài quá thì voice AI đọc bị hụt hơi và người nghe mất mạch.

**Nhiều thoại.** Mục tiêu khoảng 60–70 lượt thoại trong toàn bài. Thoại làm nhịp nhanh, giữ chân tốt hơn kể suông.

**Ngôi thứ nhất, thì hiện tại hoặc quá khứ gần.** Nhân vật chính xưng "tôi".

**Bối cảnh Việt Nam.** Đây là lợi thế cạnh tranh, không phải hạn chế. Dùng: ký túc xá, tuần quân sự đầu năm, căng tin trường, học bổng, đồ án, Zalo, xe máy, quán trà sữa trước cổng. Tên nhân vật thuần Việt: Linh, Ngọc, Trang, Minh Anh, Bảo Trâm, Khánh Vy.

Tránh: Bắc Kinh, tệ, WeChat, thiếu gia, tiểu thư nhà họ, cách xưng hô cổ trang. Những thứ đó tạo độ vênh với khán giả Việt.

**Giọng nhân vật chính: đanh đá nhưng có lý.** Không chửi tục, không hạ nhục ngoại hình. Cô ấy thắng bằng năng lực và bằng chứng, không bằng bạo lực.

## Bảy điều cấm

**1. Không markdown.** Không tiêu đề phần, không dấu sao, không gạch đầu dòng, không số thứ tự. Output là văn xuôi liền mạch, dán thẳng vào voice AI được ngay.

**2. Không chú thích thời lượng.** Không viết "(phút 15)" hay "[Khối 3]".

**3. Không chào kênh ở đầu.** Vào thẳng hook drama.

**4. Không viết ngắn hơn 16.000 từ.** Nếu viết xong thấy thiếu, quay lại bơm thêm ở Khối 2 và Khối 4 — hai khối này chịu được thêm chữ mà không loãng.

**5. Không nội dung 18+.** Không cảnh thân mật, không bạo lực đồ máu, không tự hại. Ngách này nhắm học sinh sinh viên, và YouTube hạn chế quảng cáo với nội dung đó.

**6. Không giữ tình tiết từ truyện tham chiếu.** Chỉ mượn motif và nhịp. Nếu thấy mình đang viết lại một cảnh có sẵn, dừng và nghĩ cảnh khác.

**7. Không kết thúc mở.** Kẻ xấu phải nhận kết cục rõ ràng. Khán giả ngách này nghe 60 phút để chờ khoảnh khắc đó.

## Chống trùng lặp khi sản xuất hàng loạt

Kênh ngách này cần 20–30 bài mới bắt đầu có tín hiệu. Rủi ro lớn nhất không phải viết dở, mà là **20 bài nghe giống nhau**. Khán giả nghe hết bài thứ ba là đoán được bài thứ tư, rồi bỏ.

Năm trục phải xoay vòng, không được để hai bài liên tiếp trùng:

**Khung cú lật** — bốn khung, xoay đủ vòng rồi mới lặp.

**Hoàn cảnh nhân vật chính** — bốn lựa chọn ở mục tham số.

**Động cơ của kẻ xấu** — đừng để lúc nào cũng là tiền. Xoay giữa: tiền, danh tiếng, ghen tị năng lực, giữ vị trí trong nhóm, che giấu một lời nói dối cũ, làm hài lòng gia đình.

**Không gian chính** — lớp học, ký túc xá, thao trường, xưởng thực hành, sân khấu hội diễn, chuyến đi thực tế, căng tin.

**Nhân vật đứng về phía nhân vật chính** — bạn thân, giáo viên, lớp trưởng, bác bảo vệ, một người từng là nạn nhân cũ, một người ngoài cuộc tình cờ.

Nếu người dùng đã làm nhiều bài và nhắc tới bài trước, hỏi họ một câu ngắn về bài gần nhất dùng khung nào, để tránh lặp. Nếu không có thông tin, tự chọn khác với khung phổ biến nhất là bằng chứng vật lý.

## Bốn lỗi làm rớt người nghe giữa chừng

**Kẻ xấu quá ngu.** Nếu kẻ xấu bị lật quá dễ, khán giả không thấy hả hê. Kẻ xấu phải có tính toán, phải phản đòn được ít nhất một lần ở khối 4, phải khiến nhân vật chính thua tạm thời.

**Nhân vật chính quá thụ động.** Nhân vật chính không được chỉ chịu đựng suốt 40 phút rồi bỗng thắng. Cô ấy phải hành động sớm — thu thập bằng chứng, hỏi đúng câu hỏi, tìm đúng người — chỉ là chưa đủ để thắng ngay.

**Đám đông vô hình.** Bốn mươi bạn cùng lớp không được là khối im lặng. Phải có ít nhất ba người có tên, có phản ứng riêng: một người bênh vực yếu ớt, một người hùa theo kẻ xấu, một người im lặng rồi đổi phe ở khối 5.

**Cú lật đến từ hư không.** Mọi bằng chứng dùng ở khối 5 phải đã xuất hiện thoáng qua ở khối 2 hoặc 3. Người nghe phải có cảm giác "đáng lẽ mình nhận ra rồi" chứ không phải "sao tự nhiên lại có cái này".

## Cách viết đủ 16.000 từ

Viết dài không phải là viết lan man. Bốn kỹ thuật bơm chữ mà vẫn giữ nhịp:

**Chi tiết giác quan.** Thay vì "cô ta bước vào lớp", viết mùi nước hoa, tiếng giày, ánh mắt đám đông quay theo.

**Độc thoại nội tâm.** Sau mỗi lần đụng độ, cho nhân vật chính nghĩ 100–200 từ. Đây là chỗ khán giả đồng cảm.

**Thoại của nhân vật phụ.** Bạn thân bình luận, đám đông xì xào, giáo viên hỏi han. Mỗi giọng thêm vào là thêm 200–400 từ mà không làm chậm truyện.

**Cảnh song song.** Chèn cảnh nhân vật chính làm việc riêng — học bài, làm đồ án, gọi điện về nhà. Vừa bơm chữ vừa xây dựng nhân vật.

Đừng bơm bằng cách lặp lại ý đã nói. Người nghe nhận ra ngay và bỏ đi.

## Output

Giao đúng theo thứ tự này:

Một dòng duy nhất báo tổng số từ, ví dụ: `Kịch bản: 16.840 từ, ước tính 57 phút.`

Một dòng báo bốn tham số đã dùng, để người dùng tránh trùng ở bài sau, ví dụ: `Cú lật: bằng chứng vật lý. Nhân vật chính: nghèo. Tình cảm: mờ. Động cơ kẻ xấu: tiền.`

Nếu đầu vào là truyện tham chiếu, thêm một dòng: `Bản gốc dựng theo motif, không dùng tình tiết từ nguồn tham chiếu.`

Sau đó là toàn bộ kịch bản, văn xuôi liền mạch, không có gì khác.

Nếu kịch bản quá dài để giao trong một lượt, chia thành nhiều lượt và báo rõ đang ở phần mấy, nhưng không chèn tiêu đề phần vào trong văn bản.

## Kiểm tra trước khi giao

1. Đủ 16.000 từ chưa? Đếm thật, không ước lượng.
2. Có markdown, tiêu đề phần, hay chú thích nào lọt vào không?
3. Hook ở Khối 1 có nêu thẳng hành động phi lý chưa, hay còn vòng vo?
4. Khối 4 có đủ 3–4 lần leo thang chưa?
5. Khối 5 có đủ ba yếu tố (bằng chứng, người xác nhận, phản ứng đám đông) chưa?
6. Kẻ xấu có nhận kết cục rõ ràng chưa?
7. Có lọt tên riêng Trung Quốc, đơn vị tiền tệ Trung Quốc, hay bối cảnh Trung Quốc nào không?
8. Mục tiêu nhân vật chính nêu ở Khối 2 có được giải quyết ở Khối 6 không?
9. Số lượt thoại có đạt khoảng 60 chưa?
10. Có nội dung 18+ hay bạo lực nặng nào không?
11. Kẻ xấu có phản đòn được ít nhất một lần ở khối 4 chưa, hay bị lật quá dễ?
12. Có ít nhất ba nhân vật phụ có tên và có phản ứng riêng chưa?
13. Bằng chứng dùng ở khối 5 đã xuất hiện thoáng qua ở khối 2 hoặc 3 chưa?
14. Đã báo lại cho người dùng biết bài này dùng khung cú lật nào, để lần sau họ tránh trùng chưa?
