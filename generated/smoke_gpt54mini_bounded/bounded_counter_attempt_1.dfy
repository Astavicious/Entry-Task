class Counter {
  var maximum: nat
  var counter: nat

  predicate Valid() reads this
  {
    counter <= maximum
  }

  constructor (max: nat)
    ensures Valid()
    ensures maximum == max
    ensures counter == 0
  {
    maximum := max;
    counter := 0;
  }

  method Increment()
    requires Valid()
    modifies this
    ensures Valid()
    ensures maximum == old(maximum)
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
    ensures maximum == old(maximum)
    ensures counter == 0
  {
    counter := 0;
  }
}
