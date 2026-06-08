<script>
import BaseProductPermission from "./BaseProductPermission";

export default {
  name: "ProductGroupPermission",
  mixins: [ BaseProductPermission ],
  props: {
    title: { type: String, default: "Group permissions" },
    label: { type: String, default: "Group name" },
    icon: { type: String, default: "mdi-account-group-outline" }
  }
};
</script>
