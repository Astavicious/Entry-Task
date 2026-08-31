class Account {
  var balance: int

  constructor(initBalance: int)
    requires initBalance >= 0
    ensures balance == initBalance
  {
    balance := initBalance;
  }

  method Transfer(to: Account, amount: int)
    requires to != this
    requires amount >= 0
    requires amount <= balance
    requires to.balance >= 0
    modifies this, to
    ensures balance == old(balance) - amount
    ensures to.balance == old(to.balance) + amount
    ensures balance >= 0
    ensures to.balance >= 0
    ensures balance + to.balance == old(balance) + old(to.balance)
  {
    balance := balance - amount;
    to.balance := to.balance + amount;
  }
}
