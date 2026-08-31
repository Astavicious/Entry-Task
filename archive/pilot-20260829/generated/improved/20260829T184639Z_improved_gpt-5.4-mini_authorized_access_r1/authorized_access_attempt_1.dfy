class ProtectedResource {
  var authorizedUsers: set<string>

  constructor ()
    ensures authorizedUsers == {}
  {
    authorizedUsers := {};
  }

  predicate Authorized(user: string)
    reads this
  {
    user in authorizedUsers
  }

  method GrantAuthorization(user: string)
    modifies this
    ensures Authorized(user)
    ensures authorizedUsers == old(authorizedUsers) + {user}
  {
    authorizedUsers := authorizedUsers + {user};
  }

  method RevokeAuthorization(user: string)
    modifies this
    ensures !Authorized(user)
    ensures authorizedUsers == old(authorizedUsers) - {user}
  {
    authorizedUsers := authorizedUsers - {user};
  }

  method RequestAccess(user: string) returns (granted: bool)
    ensures granted <==> Authorized(user)
    ensures !Authorized(user) ==> !granted
    ensures granted ==> Authorized(user)
  {
    granted := user in authorizedUsers;
  }
}
