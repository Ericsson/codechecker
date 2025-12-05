export function useToCSV() {
  /**
   * Exports the given data with the given file name.
   * @param {Array.<Array.<string>>} data - csv data. The first item is the
   * header and other items represent rows.
   * @param {string} fileName - default file name for export.
   */
  function toCSV(data, fileName) {
    const _content = data.map(_d => _d.join(",")).join("\n");

    const _csvContent = `data:text/csv;charset=utf-8,${
      encodeURIComponent(_content)}`;

    const _link = document.createElement("a");
    _link.setAttribute("href", _csvContent);
    _link.setAttribute("download", fileName);

    document.body.appendChild(_link);  
    _link.click();

    document.body.removeChild(_link);
  }

  return {
    toCSV
  };
}
