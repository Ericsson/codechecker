all:
	javac files/Assign.java
	spotbugs -xml:withMessages -effort:max -low -output ./assign.xml -textui files/Assign.class
clean:
	rm Assign.class
