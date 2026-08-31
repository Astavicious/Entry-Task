class AccessControl {
  var authorizedUsers: set<int>

  constructor ()
    ensures authorizedUsers == {}
  {
    authorizedUsers := {};
  }

  method GrantAuthorization(user: int)
    modifies this
    ensures authorizedUsers == old(authorizedUsers) + {user}
    ensures user in authorizedUsers
  {
    authorizedUsers := authorizedUsers + {user};
  }

  method RevokeAuthorization(user: int)
    modifies this
    ensures authorizedUsers == old(authorizedUsers) - {user}
    ensures user !in authorizedUsers
  {
    authorizedUsers := authorizedUsers - {user};
  }

  method RequestAccess(user: int) returns (granted: bool)
    ensures granted <==> user in authorizedUsers
    ensures user !in authorizedUsers ==> !granted
    ensures granted ==> user in authorizedUsers
  {
    granted := user in authorizedUsers;
  }
}
