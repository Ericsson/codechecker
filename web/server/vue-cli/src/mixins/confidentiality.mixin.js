import { Confidentiality } from "@cc/prod-types";

export default {
  methods: {
    confidentialityFromCodeToString(confiCode) {
      switch (confiCode) {
      case Confidentiality.CONFIDENTIAL:
        return "Confidential classified";
      case Confidentiality.INTERNAL:
        return "Internal classified";
      case Confidentiality.OPEN:
        return "Open classified";
      default:
        return "";
      }
    },

    confidentialityFromStringToCode(confiString) {
      switch (confiString) {
      case "Confidential classified":
        return Confidentiality.CONFIDENTIAL;
      case "Internal classified":
        return Confidentiality.INTERNAL;
      case "Open classified":
        return Confidentiality.OPEN;
      default:
        return -1;
      }
    },

    confidentialities() {
      return Object.keys(Confidentiality).map(c =>
        this.confidentialityFromCodeToString(Confidentiality[c]));
    },
  }
};
