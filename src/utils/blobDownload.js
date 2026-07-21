export function ensurePdfBlob(blob, contentType) {
  if (!(blob instanceof Blob)) {
    throw new Error('Invalid file payload.');
  }
  if (blob.type === 'application/pdf') return blob;
  if (contentType?.includes('application/pdf')) {
    return new Blob([blob], { type: 'application/pdf' });
  }
  return blob;
}

export function ensureZipBlob(blob, contentType) {
  if (!(blob instanceof Blob)) {
    throw new Error('Invalid file payload.');
  }
  if (blob.type === 'application/zip') return blob;
  if (contentType?.includes('application/zip') || !blob.type || blob.type === 'application/octet-stream') {
    return new Blob([blob], { type: 'application/zip' });
  }
  return blob;
}

export function triggerBlobDownload(blob, filename) {
  if (!(blob instanceof Blob)) {
    throw new Error('Invalid file payload.');
  }
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export function revokeObjectUrlLater(objectUrl, delayMs = 60_000) {
  if (!objectUrl) return;
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), delayMs);
}
