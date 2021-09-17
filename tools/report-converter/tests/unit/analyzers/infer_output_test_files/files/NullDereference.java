public class NullDereference {
  static Integer foo() {
    return null;
  }

  public static void main(String args[]) {
    Integer i = foo();
    i.toString();   // dereferencing p, potential NPE
  }
}
