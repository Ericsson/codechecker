<script>
import BaseProductPermission from "./BaseProductPermission";

export default {
  name: "ProductUserPermission",
  mixins: [ BaseProductPermission ],
  props: {
    title: { type: String, default: "User permissions" },
    label: { type: String, default: "User name" }
  }
};
</script>
