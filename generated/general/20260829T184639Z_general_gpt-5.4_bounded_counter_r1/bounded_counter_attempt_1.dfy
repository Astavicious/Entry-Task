class Counter {
  var counter: nat
  var maximum: nat

  predicate Valid()
    reads this
  {
    counter <= maximum
  }

  constructor (max: nat)
    ensures Valid()
    ensures counter == 0
    ensures maximum == max
  {
    maximum := max;
    counter := 0;
  }

  method Increment()
    requires Valid()
    modifies this
    ensures Valid()
    ensures maximum == old(maximum)
    ensures if old(counter) < maximum then counter == old(counter) + 1 else counter == old(counter)
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
    ensures maximum == old(maximum)
  {
    counter := 0;
  }
}
