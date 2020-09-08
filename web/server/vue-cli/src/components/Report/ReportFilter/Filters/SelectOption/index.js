import Items from "./Items";
import ItemsSelected from "./ItemsSelected";
import SelectedToolbarTitleItems from "./SelectedToolbarTitleItems";
import SelectOption from "./SelectOption";

/**
* Returns true if the filter is changed, else false.
*/
function filterIsChanged(a, b) {
  if (a.length !== b.length) return true;

  const curr = a.map(item => item.title).sort();
  const prev = b.map(item => item.title).sort();

  for (let i = 0; i < curr.length; ++i)
    if (curr[i] !== prev[i]) return true;

  return false;
}

export {
  Items,
  ItemsSelected,
  SelectedToolbarTitleItems,
  SelectOption,
  filterIsChanged
};
