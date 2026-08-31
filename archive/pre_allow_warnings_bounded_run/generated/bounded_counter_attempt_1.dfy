class Counter {
  var counter: int
  const maximum: int

  predicate Valid()
    reads this
  {
    maximum >= 0 && 0 <= counter <= maximum
  }

  constructor (maximum: int)
    requires maximum >= 0
    ensures this.maximum == maximum
    ensures counter == 0
    ensures Valid()
  {
    this.maximum := maximum;
    counter := 0;
  }

  method Increment()
    modifies this
    requires Valid()
    ensures maximum == old(maximum)
    ensures old(counter) < old(maximum) ==> counter == old(counter) + 1
    ensures old(counter) >= old(maximum) ==> counter == old(counter)
    ensures 0 <= counter <= maximum
  {
    if counter < maximum {
      counter := counter + 1;
    }
  }

  method Reset()
    modifies this
    requires Valid()
    ensures maximum == old(maximum)
    ensures counter == 0
    ensures 0 <= counter <= maximum
  {
    counter := 0;
  }
}
