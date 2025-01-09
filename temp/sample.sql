CREATE PROCEDURE ManageEmployeeData
    @Operation NVARCHAR(10), -- 'INSERT', 'UPDATE', or 'GET'
    @EmployeeID INT = NULL,
    @FirstName NVARCHAR(50) = NULL,
    @LastName NVARCHAR(50) = NULL,
    @Position NVARCHAR(50) = NULL,
    @Salary DECIMAL(18, 2) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Check which operation is requested
    IF @Operation = 'INSERT'
    BEGIN
        -- Insert new employee data
        INSERT INTO Employees (FirstName, LastName, Position, Salary)
        VALUES (@FirstName, @LastName, @Position, @Salary);

        PRINT 'New employee inserted successfully.';
    END
    ELSE IF @Operation = 'UPDATE'
    BEGIN
        -- Validate EmployeeID is provided
        IF @EmployeeID IS NULL
        BEGIN
            PRINT 'Error: EmployeeID is required for UPDATE operation.';
            RETURN;
        END

        -- Update existing employee data
        UPDATE Employees
        SET
            FirstName = ISNULL(@FirstName, FirstName),
            LastName = ISNULL(@LastName, LastName),
            Position = ISNULL(@Position, Position),
            Salary = ISNULL(@Salary, Salary)
        WHERE EmployeeID = @EmployeeID;

        PRINT 'Employee data updated successfully.';
    END
    ELSE IF @Operation = 'GET'
    BEGIN
        -- Retrieve employee data
        IF @EmployeeID IS NOT NULL
        BEGIN
            -- Get data for a specific employee
            SELECT EmployeeID, FirstName, LastName, Position, Salary
            FROM Employees
            WHERE EmployeeID = @EmployeeID;
        END
        ELSE
        BEGIN
            -- Get data for all employees
            SELECT EmployeeID, FirstName, LastName, Position, Salary
            FROM Employees;
        END
    END
    ELSE
    BEGIN
        PRINT 'Error: Invalid Operation. Use "INSERT", "UPDATE", or "GET".';
    END
END;
GO

-- Example usage:
-- EXEC ManageEmployeeData 'INSERT', NULL, 'John', 'Doe', 'Developer', 60000;
-- EXEC ManageEmployeeData 'UPDATE', 1, NULL, NULL, 'Senior Developer', 70000;
-- EXEC ManageEmployeeData 'GET';
-- EXEC ManageEmployeeData 'GET', 1;
