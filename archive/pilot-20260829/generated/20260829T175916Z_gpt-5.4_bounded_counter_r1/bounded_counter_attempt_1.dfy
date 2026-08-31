class Counter {
  var value: nat
  const maximum: nat

  predicate Valid()
    reads this
  {
    value <= maximum
  }

  constructor (max: nat)
    ensures Valid()
    ensures value == 0
    ensures maximum == max
  {
    maximum := max;
    value := 0;
  }

  method Increment()
    requires Valid()
    modifies this
    ensures Valid()
    ensures maximum == old(maximum)
    ensures old(value) < maximum ==> value == old(value) + 1
    ensures old(value) >= maximum ==> value == old(value)
  {
    if value < maximum {
      value := value + 1;
    }
  }

  method Reset()
    requires Valid()
    modifies this
    ensures Valid()
    ensures maximum == old(maximum)
    ensures value == 0
  {
    value := 0;
  }
}
