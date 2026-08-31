class Counter
{
  var counter: int
  var maximum: int

  invariant 0 <= maximum
  invariant 0 <= counter <= maximum

  constructor (maximum: int)
    requires 0 <= maximum
    ensures this.maximum == maximum
    ensures counter == 0
  {
    this.maximum := maximum;
    counter := 0;
  }

  method Increment()
    modifies this
    ensures counter == if old(counter) < maximum then old(counter) + 1 else old(counter)
  {
    if counter < maximum {
      counter := counter + 1;
    }
  }

  method Reset()
    modifies this
    ensures counter == 0
  {
    counter := 0;
  }
}
