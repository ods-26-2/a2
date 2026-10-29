export function maskCPF(value) {
  let v = String(value || "").replace(/\D/g, "");
  if (v.length > 11) v = v.substring(0, 11);
  if (v.length > 9) {
    v = v.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, "$1.$2.$3-$4");
  } else if (v.length > 6) {
    v = v.replace(/(\d{3})(\d{3})(\d{1,3})/, "$1.$2.$3");
  } else if (v.length > 3) {
    v = v.replace(/(\d{3})(\d{1,3})/, "$1.$2");
  }
  return v;
}

export function formatCpfDisplay(cpf) {
  const v = String(cpf || "").replace(/\D/g, "");
  if (v.length === 11) {
    return v.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
  }
  return v || cpf;
}

export function formatValidity(startDateStr, endDateStr) {
  try {
    const start = new Date(startDateStr);
    const end = new Date(endDateStr);

    const pad = (n) => String(n).padStart(2, "0");
    const startDay = pad(start.getDate());
    const startMonth = pad(start.getMonth() + 1);
    const startYear = start.getFullYear();

    const endDay = pad(end.getDate());
    const endMonth = pad(end.getMonth() + 1);
    const endYear = end.getFullYear();

    const startHour = `${pad(start.getHours())}:${pad(start.getMinutes())}`;
    const endHour = `${pad(end.getHours())}:${pad(end.getMinutes())}`;

    if (
      startDay === endDay &&
      startMonth === endMonth &&
      startYear === endYear
    ) {
      return `${startDay}/${startMonth}/${startYear} • ${startHour} às ${endHour}`;
    }

    return `${startDay}/${startMonth}/${startYear} às ${startHour} até ${endDay}/${endMonth}/${endYear} às ${endHour}`;
  } catch (e) {
    return `${startDateStr} às ${endDateStr}`;
  }
}

export function hexToBytes(hex) {
  if (!hex) return new Uint8Array(16);
  if (hex instanceof Uint8Array) return hex;
  if (typeof hex === "string") {
    const clean = hex.trim();
    if (/^[0-9a-fA-F]+$/.test(clean) && clean.length % 2 === 0) {
      const bytes = new Uint8Array(clean.length / 2);
      for (let i = 0; i < clean.length; i += 2) {
        bytes[i / 2] = parseInt(clean.substring(i, i + 2), 16);
      }
      return bytes;
    }
  }
  return hex;
}

export function formatDisplayDate(dateStr) {
  if (!dateStr) return "";
  try {
    const raw = String(dateStr).trim().substring(0, 10);
    const parts = raw.split("-");
    if (parts.length === 3) {
      return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    const d = new Date(raw);
    if (!isNaN(d.getTime())) {
      const pad = (n) => String(n).padStart(2, "0");
      return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
    }
    return dateStr;
  } catch {
    return dateStr;
  }
}

export function isDateExpired(dateStr) {
  if (!dateStr) return false;
  try {
    const raw = String(dateStr).trim().substring(0, 10);
    const [year, month, day] = raw.split("-").map(Number);
    const exp = new Date(year, month - 1, day, 23, 59, 59);
    return new Date() > exp;
  } catch {
    return false;
  }
}

