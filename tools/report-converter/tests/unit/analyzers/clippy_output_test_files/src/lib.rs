pub fn sample() {
    let maybe = Some("value");
    let mapped = maybe.and_then(|value| Some(value.len()));
    let unused_value = 42;
    let wrong_type: i32 = "text";
    let _ = mapped;
    let _ = wrong_type;
}
