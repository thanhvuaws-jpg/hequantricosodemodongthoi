# Mở báo cáo bằng Word, cập nhật mục lục / danh mục bảng, hình / số trang, lưu lại và xuất PDF để soát.
param([string]$Tep, [string]$Pdf)

$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
    $d = $w.Documents.Open($Tep, $false, $false)
    # cập nhật 2 lượt: lượt đầu chèn mục lục làm số trang dịch đi, lượt sau lấy số trang đúng
    for ($lan = 1; $lan -le 2; $lan++) {
        $d.Fields.Update() | Out-Null
        foreach ($toc in $d.TablesOfContents) { $toc.Update() | Out-Null }
    }
    $d.Save()
    if ($Pdf) { $d.ExportAsFixedFormat($Pdf, 17) }
    "So trang: $($d.ComputeStatistics(2))"
    "So muc luc: $($d.TablesOfContents.Count)"
    $d.Close($false)
} finally {
    $w.Quit()
}
