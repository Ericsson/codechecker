import prettifyDate from './prettify-date';
import truncate from './truncate';

export default {
  install(Vue) {
    Vue.filter('truncate', truncate);
    Vue.filter('prettifyDate', prettifyDate);
  }
}
