class Counter {
  var counter: int
  const maximum: int

  predicate Valid()
    reads this
  {
    0 <= counter <= maximum
  }

  constructor(maximum: int)
    requires maximum >= 0
    ensures this.maximum == maximum
    ensures counter == 0
    ensures Valid()
  {
    this.maximum := maximum;
    counter := 0;
  }

  method Increment()
    requires Valid()
    modifies this
    ensures Valid()
    ensures old(counter) < maximum ==> counter == old(counter) + 1
    ensures old(counter) >= maximum ==> counter == old(counter)
  {
    if counter < maximum {
      counter := counter + 1;
    }
  }

  method Reset()
    requires Valid()
    modifies this
    ensures Valid()
    ensures counter == 0
  {
    counter := 0;
  }
}
