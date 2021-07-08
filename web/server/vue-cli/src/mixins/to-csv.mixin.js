export default {
  methods: {
    /**
     * Exports the given data with the given file name.
     * @param {Array.<Array.<string>>} data - csv data. The first item is the
     * header and other items represent rows.
     * @param {string} fileName - default file name for export.
     */
    toCSV(data, fileName) {
      const content = data
        .map(d => d.join(",") + "\r\n")
        .join("")
        // Hashmark (#) is a valid URL character but it starts the hash
        // fragment and for this reason it needs to be escaped.
        .replaceAll("#", encodeURIComponent("#"));

      const csvContent = `data:text/csv;charset=utf-8,${content}`;

      const link = document.createElement("a");
      link.setAttribute("href", csvContent);
      link.setAttribute("download", fileName);

      document.body.appendChild(link);  
      link.click();

      document.body.removeChild(link);
    }
  }
};
