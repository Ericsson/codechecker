import truncate from './truncate';

export default {
  install(Vue) {
    Vue.filter('truncate', truncate);
  }
}
