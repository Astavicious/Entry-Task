class AccessControl {
  var authorized: set<string>

  constructor ()
    ensures authorized == {}
  {
    authorized := {};
  }

  function IsAuthorized(user: string): bool
    reads this
  {
    user in authorized
  }

  method GrantAuthorization(user: string)
    modifies this
    ensures authorized == old(authorized) + {user}
  {
    authorized := authorized + {user};
  }

  method RevokeAuthorization(user: string)
    modifies this
    ensures authorized == old(authorized) - {user}
  {
    authorized := authorized - {user};
  }

  method RequestAccess(user: string) returns (granted: bool)
    ensures granted <==> user in authorized
    ensures !granted || user in authorized
  {
    granted := user in authorized;
  }
}
