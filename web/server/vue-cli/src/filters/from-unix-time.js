import { format, fromUnixTime as fromUnixTimestamp } from "date-fns";

export default function fromUnixTime(
  timestamp,
  dateFormat="yyyy-MM-dd HH:mm:ss"
) {
  return format(fromUnixTimestamp(timestamp), dateFormat);
}
