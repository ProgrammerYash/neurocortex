export function buildXLSX(headers, rows) {
  // Generates an XML-based .xls file that Excel/Sheets opens natively.
  const esc = v => String(v ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const headerRow = headers.map(h=>`<Cell><Data ss:Type="String">${esc(h)}</Data></Cell>`).join("");
  const dataRows  = rows.map(r =>
    "<Row>"+r.map(v=>`<Cell><Data ss:Type="${typeof v==="number"?"Number":"String"}">${esc(v)}</Data></Cell>`).join("")+"</Row>"
  ).join("\n");
  return `<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="NeuroCortex"><Table><Row>${headerRow}</Row>\n${dataRows}</Table></Worksheet></Workbook>`;
}
export function safeDownload(content, filename, mime) {
  try {
    const blob = new Blob([content], {type: mime});
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000); // prevent memory leak
  } catch(e) { console.error("Download failed:", e); alert("Download failed: "+e.message); }
}
